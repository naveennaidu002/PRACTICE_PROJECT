from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceExistsError
from config import settings
import logging

# Application logger
logger = logging.getLogger("AI DataExplorer")
logger.setLevel(logging.DEBUG)

# Cosmosdb Client
class azureCosmosDb:
    def __init__(self, containerName):
        self.cosmoUrl = settings.storage_dburl
        self.cosmoKey = settings.storage_dbsecretkey
        self.databaseName = settings.storage_dbname
        self.containerName = containerName
        
        self.client = CosmosClient(self.cosmoUrl, credential=self.cosmoKey)
        self.database = self.client.get_database_client(self.databaseName)
        self.container = self.database.get_container_client(self.containerName)

    def insertRecord(self, payload):
        # Method to insert a record
        try:
            resp = self.container.create_item(payload)
            return {
                "status": f"Record inserted successfully to {self.containerName}",
                "response": resp
            }, 200
        except CosmosResourceExistsError:
            return {
                "status": f"Record with id {payload.get('id')} already exists in {self.containerName}",
                "error": "ConflictError"
            }, 409
        except CosmosHttpResponseError as e:
            return {
                "status": "Failed to insert record due to Cosmos error",
                "error": str(e)
            }, 500

    def upsertRecord(self, payload):
        # Method to upsert a record
        logger.info("Payload: %s", payload)
        resp = self.container.upsert_item(payload)
        return {"status": f"Record inserted successfully to {self.containerName}", "response": resp}

    def updateRecord(self, itemid, payload):
        # Method to update a record
        resp = self.container.replace_item(item=itemid, body=payload)
        return {"status": f"Record updated successfully to {self.containerName}", "response": resp}

    def fetchRecord(self, query, partition_key=False):
        # Method to fetch record
        if not partition_key:
            messages = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        else:
            messages = list(self.container.query_items(query=query, partition_key=partition_key))
        return {"status": f"Record details fetched successfully from {self.containerName}", "response": messages}

# Initializing messages ...
message_client = azureCosmosDb('messages')

# Initializing chatSessions
session_client = azureCosmosDb('chatSessions')

ahrf_county_user_prompts = [
    "Which counties have the highest number of dentists per 100,000 population?",
    "How many dentists per 100,000 population are there in Los Angeles County?",
    "What is the number of orthopedic surgeons by county in Maryland?",
    "What is the dentist-to-population ratio by county in Texas?",
]

ahrf_state_user_prompts = [
    "How many dentists are practicing in California?",
    "How many female dentists are in Arizona compared to California?",
    "How many dental providers are practicing in California?",
    "What percentage of families live below the poverty level in Washington State?",
    "What is the dentist-to-population ratio in New York?",
    "How has the number of dentists in Texas changed over the last few years?",
    "How many medical providers are practicing in Arizona?",
]

merative_user_prompts = [
    "How many people were diagnosed with diabetes in 2023?",
    "For 2023, how many patients with Medicare received annual wellness visit CPT codes?",
    "Provide a 2023 breakdown of dental claims categorized by gender and segmented by line of business (Commercial, Medicaid and Medicare).",
    "What are the 25 most frequently performed dental treatments in 2023?",
    "Calculate the percentage for 2023 where the numerator is the count of distinct children aged 1-18 who received at least two topical fluoride applications, and the denominator is the count of all distinct children aged 1-18 who received any dental claims, based on Merative Claims Data with distinct claim headers.",
    "Calculate the percentage for 2023 where the numerator is the count of distinct children aged 1-18 who received at least two topical fluoride applications and at least one oral evaluation (using specific CDT codes), and the denominator is the count of all distinct children aged 1-18 who received dental claims, based on Merative Claims Data with distinct claim headers.",
    "Calculate the totals for commercial and Medicare patients over age 17 with a Sjogren's syndrome diagnosis who had any dental claims after their diagnosis in 2023, using distinct claim headers.",
    "How many distinct inpatient claims were filed by patients who have diabetes mellitus in 2023?",
    "How many distinct individuals had restorative procedures (CDT/CPT) across all years of data?",
    "For 2023, how many individuals were diagnosed with diabetes and had a periodontal visit?"
]

hpsa_user_prompts = [
    "Which are the top 5 counties with the highest population-to-provider ratio in HPSA designated regions for dental care?",
    "What two HPSA counties are farthest away from reaching their HPSA goal?",
    "How many dental HPSAs were there in 2022?",
    "Which state had the highest number of HPSA-designated cities after January 31, 2020?",
    "What are the five states with the highest number of HPSA-designated counties?",
    "Which counties designated as HPSAs have the highest provider-to-population ratios, and what is their rural or urban status?"
]

sohea_user_prompts = [
    "What percentage of the population has lost all their teeth?",
    "What is the percentage of the population without dental insurance by race?",
    "What is the percentage of those without dental insurance who have lost at least one tooth compared to those who are insured, including confidence intervals?",
    "What percentage of Americans clean between their teeth using a Waterpik?",
    "How many adults visited a dentist in 2024 but did not visit one in 2023?",
    "What percentage of American adults have both private medical and dental insurance?",
    "How many individuals are present in every year of data? Provide an unweighted response.",
    "What is the difference in annual dentist visit rates between older and younger people, and is it statistically significant?",
    "What percentage of people have had all teeth removed in 2024 and 2025 combined? Provide a weighted response.",
    "What is the count of people who have dental insurance?",
    "What is the count of people who have dental insurance and have lost at least one tooth?",
    "What is the percentage of people with dental insurance who have lost all their teeth?",
    "What percentage of people have had all teeth removed in 2025? Provide a weighted response",
    "What percentage of American adults have private dental insurance?",
    "What were the percentages for all possible reasons an individual did not visit an oral health provider about a dental symptom?"
]

research_user_prompts = [
    "How many children and adults go to an emergency department for dental care?",
    "What systemic health conditions are linked with poor oral health?",
    "What research has CareQuest Institute published on links between oral health and overall health?",
    "How many adults saw a dentist in the past year? How does this utilization rate differ by income/dental education status, etc.?",
    "Summarize the findings from each article that discusses differences in dental care access between urban and rural areas."
]

dqddma_user_prompts = []

source_specific_user_prompts_guide_book = {
    "ahrf": {
        "county": {
            "title": "County-Level Questions (Local Focus)",
            "questions": ahrf_county_user_prompts
        },
        "state": {
            "title": "State-Level Questions (Local Focus)",
            "questions": ahrf_state_user_prompts
        },
        "general": {
            "title": "",
            "questions": []
        }
    },
    "dqddma": {
        "county": {
            "title": "",
            "questions": []
        },
        "state": {
            "title": "",
            "questions": []
        },
        "general": {
            "title": "",
            "questions": dqddma_user_prompts
        }
    },
    "sohea": {
        "county": {
            "title": "",
            "questions": []
        },
        "state": {
            "title": "",
            "questions": []
        },
        "general": {
            "title": "",
            "questions": sohea_user_prompts
        }
    },
    "hpsa": {
        "county": {
            "title": "",
            "questions": []
        },
        "state": {
            "title": "",
            "questions": []
        },
        "general": {
            "title": "",
            "questions": hpsa_user_prompts
        }
    },
    "merative": {
        "county": {
            "title": "",
            "questions": []
        },
        "state": {
            "title": "",
            "questions": []
        },
        "general": {
            "title": "",
            "questions": merative_user_prompts
        }
    },
    "research": {
        "county": {
            "title": "",
            "questions": []
        },
        "state": {
            "title": "",
            "questions": []
        },
        "general": {
            "title": "",
            "questions": research_user_prompts
        }
    }
}

source_specific_user_prompts = {
    "ahrf": {
        "state": ahrf_state_user_prompts,
        "county": ahrf_county_user_prompts
    },
    "merative": merative_user_prompts,
    "hpsa": hpsa_user_prompts,
    "sohea": sohea_user_prompts,
    "dqddma": dqddma_user_prompts
}