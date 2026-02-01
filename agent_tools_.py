from databricks import sql
from typing import Annotated
from config import settings, medical_codes, read_sohea_mapping_file, tooth_codes
from langchain.agents import tool
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery
from langchain_openai import AzureOpenAIEmbeddings
import httpx
import json

http_client = httpx.Client(verify=False)

# Langchain azure openai embeddings
embeddings_connector = AzureOpenAIEmbeddings(
    azure_endpoint=settings.LLM_Config['embedding']['endpoint'],
    api_key=settings.LLM_Config['embedding']['subscription_key'],
    api_version=settings.LLM_Config['embedding']['api_version'],
    model=settings.LLM_Config['embedding']['model_name'],
    http_client=httpx.Client(verify=False)
)

# Method to execute generated sql query
def sql_query_executor(sql_query):
    try:
        databricks_connection = sql.connect(
            server_hostname=settings.dbhostname,
            http_path=settings.sqlurl,
            access_token=settings.dbaccesstoken,
            verify=False
        )
        cursor = databricks_connection.cursor()
        try:
            cursor.execute(sql_query)
            results = cursor.fetchall()
            return results
        finally:
            cursor.close()
            databricks_connection.close()
    except Exception as e:
        return f"Failed Error: {str(e)}"

@tool
def fetch_record(sql_query: Annotated[str, "SQL Query to fetch records from the database."]):
    """
    Executes the provided SQL query against the connected database and returns the fetched results.

    Args:
        sql_query (str): The SQL query string to execute.

    Returns:
        list: A list of rows fetched from the database or an error message string.
    """
    return sql_query_executor(sql_query)

def catalog_query_exec(table_name):
    query = f"DESCRIBE {table_name}"
    return sql_query_executor(query)

# Method to execute AI Search query
def run_query(index_name, reqbody, select_fields_, top_=50):
    search_client = SearchClient(
        endpoint=settings.search_endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(settings.search_key)
    )
    
    embedded_query = embeddings_connector.embed_query(reqbody['query'])

    # Vectorized query
    vector_query = VectorizedQuery(
        vector=embedded_query,
        k_nearest_neighbors=20,
        fields="content_vector"
    )

    formatted_context = []

    try:
        if reqbody['datasource'].lower() == 'research':
            datasource_filter = f"datasource eq '{reqbody['datasource'].lower()}'"
        else:
            datasource_filter = f"datasource eq '{reqbody['datasource'].upper()}'"
        
        targettables = reqbody.get('selected_table_name', [])
        targetfilenames = reqbody.get('filenames', [])

        if targettables:
            targettable_filter = " or ".join(f"targettable eq '{t}'" for t in targettables)
            targettable_filter = f"({targettable_filter})"
            combined_filter = f"{datasource_filter} and {targettable_filter}"
        elif targetfilenames:
            targetfilenames_filter = " or ".join(f"filename eq '{t}'" for t in targetfilenames)
            targetfilenames_filter = f"({targetfilenames_filter})"
            combined_filter = f"{datasource_filter} and {targetfilenames_filter}"
        else:
            combined_filter = datasource_filter

        if 'yearnumber' in reqbody:
            combined_filter += f" and yearnumber eq '{reqbody['yearnumber']}'"

        print(f"combined_filter", combined_filter)

        docs = search_client.search(
            search_text=reqbody['query'],
            vector_queries=[vector_query],
            top=top_,
            select=select_fields_,
            semantic_configuration_name="sem-config",
            query_type="semantic",
            filter=combined_filter
        )

        for doc in docs:
            print('Search Score', doc.get('@search.score'))
            row = {}
            for field in select_fields_:
                if field == 'id':
                    continue
                key = 'tablename' if field == 'targettable' else field
                row[key] = doc.get(field, '')
            formatted_context.append(row)
        
        return formatted_context

    except Exception as e:
        raise
        # return f" Error {str(e)} please inform this error to user"

@tool
def column_metadata_extractor(
    reqbody: Annotated[str, "A JSON string with query and datasource"]
) -> str:
    """
    Executes the provided query against the connected database and returns the fetched columns metadata.

    Args:
        reqbody (str): A JSON string with query and datasource.

    Returns:
        str: A string of column metadata fetched from the database.
    """
    try:
        reqbody = json.loads(reqbody)

        if 'databricks_tables' in reqbody:
            table_info = []
            for databricks_table in reqbody['databricks_tables']:
                table_info.append({"tableName": databricks_table, "metadata": catalog_query_exec(databricks_table)})
            return table_info

        if reqbody['datasource'].lower() in ['research']:
            top_docs = int(reqbody.get('top_docs', 5))
            if top_docs > 5:
                top_docs = 5
            
            select_fields = ["id", "content", "url", "title", "authors", "filename", "published_year"]
            index_name = settings.research_search_index
            formatted_context = run_query(index_name, reqbody, select_fields, top_=top_docs)
            
            if reqbody.get('whole_document_needed?', '').lower() == 'no':
                return formatted_context

            top_sections = 5
            index_name = settings.research_search_section_index
            doc_sections = []
            
            for row in formatted_context:
                reqbody['filenames'] = [row['filename']]
                print(reqbody)
                formatted_context_sections = run_query(index_name, reqbody, select_fields, top_=top_sections)
                print(formatted_context_sections)
                doc_sections.extend(formatted_context_sections)
            
            return doc_sections

        select_fields_ = ["id", "colname", "targettable", "description", "sourcetable", "query_mode", "characteristics_desc"]

        if reqbody['datasource'].lower() in ['ahrf', 'hpsa']:
            index_name = settings.semantic_search_index
            formatted_context = run_query(index_name, reqbody, select_fields_)
            return formatted_context

        elif reqbody['datasource'].lower() in ['sohea']:
            index_name = settings.sohea_search_index
            formatted_context = run_query(index_name, reqbody, select_fields_)
            return formatted_context

        if 'json' in reqbody:
            if reqbody.get('is_tooth_codes', False):
                return tooth_codes
            return {key: medical_codes[key] for key in reqbody['json_keys'] if key in medical_codes}

        if 'selected_table_name' in reqbody:
            if any(table in reqbody['selected_table_name'] for table in [
                f'{settings.db_schema}.reference.ref_cdt_code_lookup',
                f'{settings.db_schema}.reference.ref_icd_code_lookup',
                f'{settings.db_schema}.reference.ref_cpt_code_lookup'
            ]):
                index_name_ = settings.medical_code_index
                print('..... INDEXNAME', index_name_)
                select_fields = ["id", "colname", "value", "targettable", "description", "sourcetable", "query_mode"]
                formatted_context = run_query(index_name_, reqbody, select_fields, top_=100)
                return json.dumps(formatted_context)

    except Exception as e:
        return str(e)

@tool
def sohea_mapping_file_reader(reqbody):
    """
    Reads the SOHEA question mapping file.
    reqbody may be a JSON string or a dict.
    """
    if isinstance(reqbody, str):
        reqbody = json.loads(reqbody)
    
    filename = reqbody.get("filename")
    return read_sohea_mapping_file(filename)

# Initialized Agent Tools
tools = [fetch_record]
meta_data_tools_ = [column_metadata_extractor]
sohea_agent_tools = [sohea_mapping_file_reader]