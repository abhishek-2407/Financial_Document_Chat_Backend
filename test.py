from utils.llm_calling import call_openai

import psycopg2
import uuid
import json

    # 'section_1' : 'Assets',
    # 'section_2' : 'Current Assets',
    # 'section_3' : 'Financial Assets',


data = """
## Consolidated Balance Sheet **As at March 31, 2025** ### All Extracted Text The image contains a consolidated balance sheet as at March 31, 2025. It includes sections for Assets and Equity and Liabilities. Each item in the balance sheet is presented with its corresponding note and values for two different dates: March 31, 2025, and March 31, 2024. The values are presented in Crore. Under Assets, there are Non-current assets and Current assets. Non-current assets include: * Property, plant and equipment * Capital work-in-progress * Right of use assets * Investment properties * Goodwill * Other intangible assets * Intangible assets under development * Equity accounted investments * Financial assets (with sub-categories: Investments, Loans, Derivatives, Other financial assets) * Non-current tax assets (Net) * Deferred tax assets (Net) * Other non-current assets * Non-current assets classified as held for sale Total non-current assets are also summarized. Current assets include: * Inventories * Financial assets (with sub-categories: Investments, Trade receivables, Cash and cash equivalents, Bank balances other than cash and cash equivalents, Loans, Derivatives, Other financial assets) * Current tax assets (Net) * Other current assets Total current assets are also summarized. Finally, Total assets are presented. Under Equity and Liabilities, there is Equity and Liabilities. Equity includes: * Equity share capital * Other equity * Equity attributable to owners of the Company * Non-controlling interests Total equity is summarized. Liabilities are categorized into Non-current liabilities and Current liabilities. Non-current liabilities include: * Financial liabilities (with sub-categories: Borrowings, Lease liabilities, Derivatives, Other financial liabilities) * Provisions * Employee benefit obligations * Deferred tax liabilities (Net) * Other non-current liabilities Total non-current liabilities are summarized. Current liabilities include: * Financial liabilities (with sub-categories: Borrowings, Lease liabilities, Supplier's credit, Trade payables (with further sub-categorization for outstanding dues of micro and small enterprises and other than micro and small enterprises), Derivatives, Other financial liabilities) * Provisions * Employee benefit obligations * Contract liabilities * Current tax liabilities (Net) * Other current liabilities Total current liabilities are summarized. Total liabilities are summarized. Total equity and liabilities are also summarized. At the end of the document, there is a section about "Notes forming part of consolidated financial statements" which indicates a range of notes from 1-39. The document also contains information regarding the auditors: For Price Waterhouse & Co Chartered Accountants LLP, with Firm Registration No. 304026E/E-300009. Sarah George is listed as Partner with Membership No. 045255. The place of audit is Mumbai and the date is May 20, 2025. There is also a section "For and on behalf of the Board of Directors" which lists Bharat Goenka as Chief Financial Officer, Geetika Anand as Company Secretary, Satish Pai as Managing Director (DIN-06646758), and Arun Adhikari as Director (DIN-00591057). The document also states "Hindalco Industries Limited Integrated Annual Report 2024-25". ### Tables #### Consolidated Balance Sheet: Assets | ASSETS | Note | As at 31/03/2025 | As at 31/03/2024 | | :----------------------------------------------------- | :--- | :--------------- | :--------------- | | **Non-current assets** | | | | | Property, plant and equipment | 3A | 81,739 | 77,151 | | Capital work-in-progress | 3B | 27,023 | 14,591 | | Right of use assets | 3C | 2,498 | 2,547 | | Investment properties | 3E | 45 | 46 | | Goodwill | 4 | 26,683 | 26,075 | | Other intangible assets | 3F | 5,591 | 5,991 | | Intangible assets under development | 3F | 374 | 276 | | Equity accounted investments | 1C | 124 | 110 | | Financial assets | 5 | | | | Investments | 5A | 13,502 | 12,062 | | Loans | 5C | 6 | 7 | | Derivatives | 5D | 139 | 91 | | Other financial assets | 5E | 1,082 | 3,737 | | Non-current tax assets (Net) | 6B | 14 | 7 | | Deferred tax assets (Net) | 6C (a)| 1,691 | 1,184 | | Other non-current assets | 7 | 3,521 | 5,689 | | **Total non-current assets** | | **164,032** | **149,564** | | **Current assets** | | | | | Inventories | 8A | 48,801 | 40,812 | | Financial assets | 5 | | | | Investments | 5B | 10,532 | 3,272 | | Trade receivables | 5F | 19,834 | 16,404 | | Cash and cash equivalents | 5G | 9,808 | 11,816 | | Bank balances other than cash and cash equivalents | 5H | 1,038 | 871 | | Loans | 5C | 7 | 32 | | Derivatives | 5D | 1,874 | 631 | | Other financial assets | 5E | 4,893 | 3,642 | | Current tax assets (Net) | 6B | 197 | 117 | | Other current assets | 7 | 4,917 | 4,702 | | Non-current assets classified as held for sale | 9 | 58 | 44 | | **Total current assets** | | **101,959** | **82,343** | | **Total assets** | | **265,991** | **231,907** | #### Consolidated Balance Sheet: Equity and Liabilities | EQUITY AND LIABILITIES | Note | As at 31/03/2025 | As at 31/03/2024 | | :-------------------------------------------------------------- | :--- | :--------------- | :--------------- | | **Equity** | | | | | Equity share capital | 10 | 222 | 222 | | Other equity | 11 | 123,487 | 105,924 | | Equity attributable to owners of the Company | | 123,709 | 106,146 | | Non-controlling interests | 12 | 12 | 11 | | **Total equity** | | **123,721** | **106,157** | | **Liabilities** | | | | | **Non-current liabilities** | | | | | Financial liabilities | 12 | | | | Borrowings | 12A | 56,217 | 47,395 | | Lease liabilities | 3D | 1,623 | 1,431 | | Derivatives | 5D | 66 | 42 | | Other financial liabilities | 12C | 465 | 314 | | Provisions | 13 | 689 | 618 | | Employee benefit obligations | 14B | 5,538 | 5,617 | | Deferred tax liabilities (Net) | 6C (b)| 10,471 | 9,344 | | Other non-current liabilities | 16 | 1,685 | 1,638 | | **Total non-current liabilities** | | **76,754** | **66,399** | | **Current liabilities** | | | | | Financial liabilities | 12 | | | | Borrowings | 12B | 5,714 | 7,106 | | Lease liabilities | 3D | 375 | 424 | | Supplier's credit | 12D | 1,713 | 4,475 | | Trade payables | | | | | (I) Outstanding dues of micro and small enterprises | 12E | 286 | 175 | | (II) Outstanding dues other than micro and small enterprises | | 40,346 | 32,683 | | Derivatives | 5D | 1,022 | 1,356 | | Other financial liabilities | 12C | 6,305 | 5,176 | | Provisions | 13 | 1,992 | 2,021 | | Employee benefit obligations | 14B | 1,417 | 1,137 | | Contract liabilities | 15 | 358 | 366 | | Current tax liabilities (Net) | 6B | 3,545 | 2,452 | | Other current liabilities | 16 | 2,443 | 1,980 | | **Total current liabilities** | | **65,516** | **59,351** | | **Total liabilities** | | **142,270** | **125,750** | | **Total equity and liabilities** | | **265,991** | **231,907** | ### Graphs/Charts Description There are no charts, graphs, or bar plots present in the image.
"""

system_prompt = """You are a json creator, extract the data out of the tables.

Based on Data just scrape the content of the table.
You must provide the whole table.

This is the json format for your response.
[
{
    'particulars' : 'name',
    'year' : '2024' in this format only,
    'values' : 'actual value', (Numeric)
    'notes' : 'notes number if mentioned',
}
]

Provide in Json format only
"""

user_prompt = f"""Data : {data}"""

print("Initiated extraction")
raw_response = call_openai(system_prompt=system_prompt,user_prompt=user_prompt,model='gpt-4o')

print("Extracted Response")
cleaned = raw_response.strip().replace("```json", "").replace("```", "").strip()


data = json.loads(cleaned)
print("Data loaded successfully")


# ---- Database connection config ----
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "dis",
    "user": "postgres",
}



# ---- Company name passed separately ----
company_name = "tata 2025"
data_type = "consolidated"

# ---- Insert function ----
def safe_float(val):
    """Convert string to float safely, return None if invalid"""
    if not val:
        return None
    val = val.replace(",", "").strip()
    try:
        return float(val)
    except ValueError:
        return None  # skip "-" or bad strings

def insert_balance_sheet_items(data, company_name):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    insert_query = """
        INSERT INTO balance_sheet (id, company_name, particulars, year, values, notes, data_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    for item in data:
        cur.execute(insert_query, (
            str(uuid.uuid4()),         # generate UUID in Python
            company_name,
            item.get("particulars"),
            int(item.get("year")),
            safe_float(item.get("values")),
            item.get("notes") if item.get("notes") else None,
            data_type
        ))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Data inserted successfully!")

insert_balance_sheet_items(data, company_name)


print(data)