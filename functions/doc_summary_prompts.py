mentioned_sections = {
    "revenue" : """abcd""",
    "": """"""
}

standard_output_template = """

      - Provide the reasons with some calculations if needed.  
      - No Conclusion is required.
      - Start with pointer directly.
      - Cover the most important and crisp pointer. Analysis should be provided not the summary.

      **Response Guideline: **
              **Response should not exceed 600 words.**
              ✅ **Emoji Formatting Rules:**  
                  - First heading should be H2 font
                  - ✅ Use checkmarks (✅) for key points and important statements.  
                  - 🔶 Use "🔶" at the start of **big headings**.  
                  - 🔸 Use "🔸" at the start of **smaller headings**.  
                  - 🚀 Use additional relevant emojis to make responses engaging.  
                  - ❌ Use "❌" for incorrect statements or warnings.  

                  ✅ **Example Response Structure:**  
                  🔶 **Overview**  
                  ✅ This feature helps improve performance.  

                  🔸 **Key Details**  
                  ✅ It supports multiple formats.  
                  ❌ It does not work with outdated versions.
      """

dynamic_sections = """
Analyze the following document and identify all the key sections that are significantly discussed. For each section, provide:

- The section title
- A short summary (2-3 lines) of the content discussed
- The page number(s) where the section appears

Respond in the following JSON format in Dict only:

- You Must cover all pages, group the similar section and pages.

{
  "sections": [
   {
    "section_title": "Section Name",
    "summary": "short summary of what is covered in this section.",
    "pages": [pages with similar sections and topics]
  },
  ...
  ]
}
"""

fixed_section_prompt = [
  {
    "volume_growth" : f"""
          Provide me the Discussion points on "Volume Growth" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """
  },
  {
    "logistic" : f"""
          Provide me the Discussion points on "Logistic" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """
  },
  {
    "rmc_vac_plus" : f"""
          Provide me the Discussion points on "RMC VAC Plus" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "taluka_ranking" : f"""
          Provide me the Discussion points on "Taluka Ranking" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "ubs-outlets" : f"""
          Provide me the Discussion points on "UBS outlets" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "actual_vs_budgeted_variable_cost" : f"""
          Provide me the Discussion points on "Actual vs Budgeted Variable Cost" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "revenue" : f"""
          Provide me the Discussion points on "Revenue" in short along with the reasons must. 
          - Compare different quarter s
          - Compare the growth of other industry with the ultratech part
          - Provide the trends for it.
          - Must provide the reasons for the points provided.
          
          {standard_output_template}
          """},
  
  {
    "progress_of_projects" : f"""
          Provide me the Discussion points on "progress of projects" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "industry_growth_vis-a-vis_utcl" : f"""
          Provide me the Discussion points on "Industry Growth vs Utcl" in short along with the reasons must, You can provide the reasons by analysing the documents.
          .
          
          Instruction :
          a.	Industry Growth Rate vs UTCL growth rate
          b.	What is the basis of growth rate of next quarter  as compared to industry expected growth rate.
          c.	Growth rate of different quarter s
          d.	Incremental demand (MnT) from Q2 of FY 22

          {standard_output_template}
          """},
  {
    "region_wise_market_share" : f"""
          Provide me the Discussion points on "Region wise market share" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "segment-wise_growth" : f"""
          Provide me the Discussion points on "segment wise growth" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "ncr" : f"""
          Provide me the Discussion points on "NCR" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "trade_ncr_vs_institutional_ncr" : f"""
          Provide me the Discussion points on "Trade NCR vs Institutional NCR" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "key_outstanding" : f"""
          Provide me the Discussion points on "Key Outstanding" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "ubs_slide" : f"""
          Provide me the Discussion points on "UBS Slide" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "sales_performance_trend" : f"""
          Provide me the Discussion points on "Sales Performance Trend" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "variable_cost" : f"""
          Provide me the Discussion points on "Variable Cost" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "fuel_mix" : f"""
          Provide me the Discussion points on "Fuel Mix" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "power_heat_consumption_vs_budget" : f"""
          Provide me the Discussion points on "Power Heat Consumption vs Budget" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "fixed_costs" : f"""
          Provide me the Discussion points on "Fixed Costs" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """
  },
  {
    "financials" : f"""
          Provide me the Discussion points on "Financials" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "overseas_operations" : f"""
          Provide me the Discussion points on "Overseas Operations" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """},
  {
    "safety" : f"""
          Provide me the Discussion points on "Safety" in short along with the reasons must, You can provide the reasons by analysing the documents.
          
          {standard_output_template}
          """
  }
]

word_file_prompt = { 
    "page_1" : """You are a points extractor from the documents mentioned.
                These are the points which you needs to extract :
                
  This is just for reference :               
  ** A. POSITIVES 

    1. VOLUME GROWTH OF N% VS INDUSTRY GROWTH OF N% in in quarter  ABD. (Take this number from Key Value Drivers Page : All India)

    2. HIGHER USE OF PET COKE FROM n% TO n% IN Q2- RESULTING IN LOWER FUEL RATE RS n/MCV VS RS n/MCV BUDGET (SLIDE 44) 

    3. LOGISTICS – LEAD LOWER BY n KMS VS BUDGET (n KMS LOWER VS Q2Quarter  ABC).  
      a. TLC AT RS n/B LOWER BY RS n PB VS LY (Budget Rs n/B) – mainly due to gain from new capacities, higher L1 sourcing and efficiencies.  

    4. CONTINUED GOOD PERFORMANCE IN BPD. EBITDA continues to be better than budget (Rs n Cr vs Rs n Cr budget), despite lower revenues vs budget (Rs n Cr vs Rs n Cr budget). ROCE at n% in Quarter ABC (Slide 35) 
      a. Liquid waterproofing adding incremental n% contribution to premium products 

    5. RMC VAC Plus – now n% of total volumes vs n% in Q2Quarter  ABC (n% in Quarter  ABC). 

    6. EXCELLENT PROGRESS ON PROJECTS - with many projects completed before schedule. 

    7. TALUKA RANKING – No 1 in n% of Taluka in (quarter or half year) vs n% in Quarter  ABC. No 1+2 in n% vs n% LY 

    8.UBS – n outlets in Qarter n vs budget of n. YoY Growth in Birla Pivot n% and UTCL brands n% 

    9. Fuel cost better in in quarter  ABD at Rs n/Mkcal vs LE of Rs n/Mkcal – due to optimized use to Petcoke 
    

  **
               
  Extract these kinds of points if available in the document mentioned .
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.            
               """,
               
  "page_2" : """  
      You are a points extractor from the documents mentioned.
      These are the points which you needs to extract. This is an example do not refer to the data from this section :
      
        B. UBS
          1. Added n new stores in in quarter  ABD (n in Quarter  ABC) vs budget of n stores. n% outlet in rural. 

          2. Sharp degrowth in retail cement sale of Express stores (n% Urban, n% Rural). Outlook? (Slide 7B) 
          
          3. Provide key KPIs in table which will also covers different quarter s information.(Provide table for this section)
          
          4. Sales performance trend (Provide reasons and a table for the trend)
          
        Extract these kinds of points if available in the document mentioned .
        Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  """,
  
  "page_3" : """  
      You are a points extractor from the documents mentioned.
      These are the points which you needs to extract. This is an example do not refer to the data from this section :
      
        C. OPERATIONS 
          1. VARIABLE COST (Slide 45): Lower by Rs n/b vs budget 
            - Raw Material Rs n/b in in quarter  ABD lower vs budget Rs n/b – due to lower cost of limestone and raw mix optimization. Learnings? Permanent savings?  

            - Additives – though lower vs budget but sharp increase in last n years; up by almost n%. Reasons? 

            - Q2 LE variable cost (slide 18) – Rs n/b vs n/b in Quarter n – whereas fuel cost Rs n/Mkcal in Q2 LE vs Rs 2018/Mkcal (additional slide). Understand?  

            - Increase in Power cost by Rs n/b vs Qn whereas Power cost has come down from Rs n/kwh in Q1 to Rs n/Kwh in Q2 – Reason? (Slide 45, 19B) 

            - Stores and Spares – Rs n/b v budget Rs n/b 
            
            - Non availability of manpower for shutdown and projects – BRC suggested to maintain a crew given the increasing scale of operations 
            
            Create a quarter wise table for this section if possible
            

          2. Fuel Mix: 
            - Indigenous coal expected to decline in Qn to n% from n% in Q2 – due to fixed contracts? (slide 18B) 

            - Reason for increase in AFR cost in Q3LE to Rs n/Mkcal from Rs n/Mkcal in Q2 (Quarter  ABC Rs n/Mkcal) – Reason?  

            - Reason for higher cost of captive mines Rs n /MKcal in in quarter  ABD vs budget Rs n/Mkcal (Rs n/Mkcal in Quarter  ABC) ? 
            
            **Create a quarter -wise table for this section if possible**

        
        Extract these kinds of points if available in the document mentioned .
        Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  """,
  
  "page_4" : """
  You are a points extractor from the documents mentioned.
  These are the points which you needs to extract. This is an example do not refer to the data from this section :
  '
    D. BPD
    
    1.	Sales Rs n Cr lower vs budget Rs n Cr?  
        a.	No of cement dealers selling BPD range has declined sharply? Understand? (slide 10B)
    2.	Waterproofing products (Slide 10B, 33): Sales at Rs n Cr vs budget Rs n Cr. UTCL was very optimistic about waterproofing segment earlier. Outlook?
        a.	No of dealers selling waterproofing products reduced to n vs n PY – Reason?
        b.	Are we facing higher competition?
        c.	How do we want to reorient? 
        
        If data is available then Create table providing quarter  information, You can Calculate and provide the information
          Revenue Gross
          EBITDA
          EBITDA %
          RoCE
          No of dealers
  '
    Extract these kinds of points if available in the document mentioned .
    Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.

  """,
  "page_5" : """
  You are a points extractor from the documents mentioned.
  These are the points which you needs to extract. This is an example do not refer to the data from this section :
  
  '
  E.	INDUSTRY GROWTH VIS-À-VIS UTCL
  
    1.	Industry growth n% vs UTCL growth n% (capturing ~n% of the incremental volume) (slide 18)
      a.	Q3 LE VOLUME GROWTH WAS EST AT n% (INDUSTRY GROWTH n%). Actual growth much lower. 
      b.	UTCL INCREMETNAL MS n% vs INCREMENTAL CAPACITY SHARE OF n% YOY? (slide 21B)
      c.	Relatively higher growth in East n% (PY n%) and Maharashtra n% (PY n%). Understand? (slide 2B)

      Cover this kind of points with supporting tables of industry growth and UTCL growth quarter wise.
      
    '
  Extract these kinds of points if available in the document mentioned .
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.

  """,
  
  "page_6" : """
  You are a points extractor from the documents mentioned.
  These are the points which you needs to extract. This is an example do not refer to the data from this section :
    '
    2.	REGION WISE MARKET SHARE, CAPACITIES AND UTILIZATION (Slide 54, 55, 56, 3B, 4B):
      a.	Sequentially MS declined in North and Maharashtra. Maharashtra Non-trade NCR increase sharply in Q3 vs Q2. Outlook? (slide 20B, 19)
      b.	Considering similar growth in Q4(quarter ) (vs Q3(quarter )) in East, Gujarat and Maharashtra, whereas other regions are expected to growth significantly higher. Since economy is expected to remain subdued in Q4(quarter ), what will drive this growth? (Slide 14B)
      c.	Over last 5 years, UTCL’s sales growth in East and Gujarat not in the same proportion as growth in capacity addition. Any opportunities? 
      
      Must provide supporting tables which consists data of Region wise Growth rates (YoY) and UTCL Zone wise market share trend
    '
  Extract these kinds of points if available in the document mentioned .
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  
  """,
  "page_7" : """
    You are a points extractor from the documents mentioned.
    These are the points which you needs to extract. This is an example do not refer to the data from this section :
    
    '
      F.	RMC (Slide 6, 30):
        1.	Volume growth of n% YoY (Slide 30). Volume n lac Cum lower vs budget n lac Cum 
        2.	No of cities and plants lower than budget (n plants vs n plants budget) – Missed opportunities?
          a.	Market share improved sequentially to n% but still lower vs Q1 n%
        3.	Value added concrete – lower at n% vs planned n%  – Outlook? 
        4.	VAC+ delta contribution declined to Rs n/Cum vs Rs n/Cum in Qn. Outlook?
        5.	New products/applications like Décor, Zip, iFloors, Rapid, Duraplus, Thermocon, Aqualseal etc – what is the potential market size and our target market share? (slide 28-29)
          a.	Hardscaping, Raft application – Understand?
        6.	RMC Ughai – marginal increase in No of days to n in Dec-24 from n in Sep-24. Outlook? 
        
        Also Generate a Table covering all these fields quarter wise:
        Particulars
        - RMC Volume (Lacs CuM)
        - RMC Trade (% of Total)
        - Contribution (Rs/CuM)
        - PBDIT (Rs Cr)
        - ROCE
        - VAC+
        - ∆ contribution of VAC+ (Rs/Cum)
        - Contribution VAC+ Rs Cr
        - Contribution Other Rs Cr

      ' 
  
    Extract these kinds of points if available in the document mentioned .
    Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  
  """,
  "page_8" : """
    You are a points extractor from the documents mentioned.
    These are the points which you needs to extract. This is an example do not refer to the data from this section :
  
    '
      G.	UTEC (SLIDE 8, 36):
        1.	Revenue at Rs n Cr - lower vs budget Rs n Cr. Paid services declining – Outlook? 
        2.	n% sites converted (out of which ~n% buying only n category) – how much is incremental due to Utec and how much is due to technical services? (slide 36)
        3.	Are we measuring Delta volume / contribution due to Utech?  
        4.	What is the value customers are seeing in Utech? IHB onboarding/Sites creation declining - Is there a need to revisit the whole concept? 
        5.	How Utec has contributed Rs n Cr sales to Birla Pivot in Q3(quarter )? What is the business model? Understand? (slide 37)

          If data is available then Create a table covering these all points for different quarter s:
            Particulars :
            -  IHB On-boarding
            -  Service Requests
            -  Total Services
            -  Net Revenue (Rs Cr)
            -  PBDIT (Rs Cr)
            -  Services (Rs Cr)
            
          If data is available then Create a table quarter wise covering these all points: 
          - Growth %	
          - Cement Only	
          - Cement + Utec + BPD	
          - Overall Trade 
            
        6.	WHRS: n% of overall power mix in Q3(quarter ) VS BUDGET n%; Q3(quarter ) n MW vs Q3(quarter ) LE n MW:
          a.	Delay in WHRS commissioning in new units, Maihar, APCW 1 & 3, and Vikram – Outlook? 
          b.	Pls provide a tally of lower WHRS generation – how much is due to delay in projects, how much due to low utilization/inefficiency etc.
          c.	PREVIOUS BRC SUGGESTION – TO TRACK EFFICIENCY OF WHRS PLANTS FOR NEW AND OLD UNITS SEPARATELY. 

        7.	SOLAR: Share of Solar in overall power mix Q3(quarter ) n% (budget n%)
          a.	Delay in RE project commissioning at RWCW, GCW, MKCW, JCW, MP Plants and KUCW – how much capacity and reason for delay? (slide 42)
          b.	Plan was to commission n MW in Q3, but only n MW got commissioned 


    '
  Extract these kinds of points if available in the document mentioned .
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  
  """,
  
  "page_9" : """
  
  You are a points extractor from the documents mentioned.
  These are the points which you needs to extract. This is an example do not refer to the data from this section :
  
  '
    H.	LOGISTICS
      1.	Logistics / TLC: Lead lower than Budget by n kms & LY by n kms; TLC lower than Budget by Rs n pb & LY by Rs n pb (slide 19)
      2.	TLC impacted by (Slide 9B)
        a.	L2 Sourcing IMPACT Rs n/b vs budget – 
          i.	Gujarat (n pb): Higher sourcing from Sewagram - Higher demand in December. Lower from Dhar, Nathdwara & Magdalla. Understand what were the issues? 
          ii.	Project Delay (n pb): Delay in Expansion & stabilisation of Arrakonam (commissioned in Sep-24), Karur (April-24) & BSBT (Dec-23) – Understand? (slide 9B)
      3.	Cement (n% vs n% YoY) and Clinker (n% vs n% YoY) L1 compliance has declined YoY (slide 16B) – opportunity? 
      
        If data is available then create a table having quarter-wise details for these sections :
          TLC :
            - Rs/bag
            - Primary lead (Kms)

  '
  Extract these kinds of points if available in the document mentioned . Do not Provide any additional information.
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  
  
  """,
  
  "page_10" : """
  You are a points extractor from the documents mentioned.
  These are the points which you needs to extract. This is an example do not refer to the data from this section :
  
  '
   I. FINANCIALS
    1. PROFITABILITY 
      Provide a table which will have UTCL Ebitda quarterwise.
      
    2. ROCE :
      Provide a table which will have UNCL, century, overall details quarterwise.
  
  '
  
  Extract these kinds of points if available in the document mentioned .
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  
  
  """,
  
  "page_11" : """
  
  You are a points extractor from the documents mentioned.
  These are the points which you needs to extract. This is an example do not refer to the data from this section :
  
  '
    J.	PROJECTS
      1.	PROJECT SPRINT (n MTPA EXPANSION) – (Slide 46)
        a.	Delay in Arrakonam hookup with ball mill - was planned by Nov-24, but now changed to Jan-25 – understand? 
        b.	Lucknow – n% fabrication and n% Erection but LE COD Feb-25. Achievable?
        c.	Durgapur Slag – n% erection but LE COD Mar-25? Achievable? 
      2.	Project Happy (slide 48):
        a.	Status of shelving Chennai BT post India Cement acquisition? 
        b.	Was to re-evaluating Mandya BT post India Cement acquisition? Status? 
        c.	Aligarh was also being evaluated vis-à-vis capacity increase at Shahjahanpur (n MnT to n MnT). 
        d.	Continuing with Pentnikota due to land and limestone availability.
  
  '
  Extract these kinds of points if available in the document mentioned . DO not add anything else.
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  
  """
               
   
                    }