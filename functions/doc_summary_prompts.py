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
          - Compare different quarters
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
          b.	What is the basis of growth rate of next quarter as compared to industry expected growth rate.
          c.	Growth rate of different quarters
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

    1. VOLUME GROWTH OF 2.7 % VS INDUSTRY GROWTH OF xxx% in Q2FY25.  

    2. HIGHER USE OF PET COKE FROM 42% TO 54% IN Q2- RESULTING IN LOWER FUEL RATE RS 1,858/MCV VS RS 1,954/MCV BUDGET (SLIDE 44) 

    3. LOGISTICS – LEAD LOWER BY 2 KMS VS BUDGET (15 KMS LOWER VS Q2FY24).  
      a. TLC AT RS 59.5/B LOWER BY RS 1.4 PB VS LY (Budget Rs 59.24/B) – mainly due to gain from new capacities, higher L1 sourcing and efficiencies.  

    4. CONTINUED GOOD PERFORMANCE IN BPD. EBITDA continues to be better than budget (Rs 24.4.1 Cr vs Rs 17.6 Cr budget), despite lower revenues vs budget (Rs 299 Cr vs Rs 422 Cr budget). ROCE at 176% in Q1FY25 (Slide 35) 
      a. Liquid waterproofing adding incremental 6.1% contribution to premium products 

    5. RMC VAC Plus – now 12.2% of total volumes vs 7.7% in Q2FY24 (11.2% in Q1FY25). 

    6. EXCELLENT PROGRESS ON PROJECTS - with many projects completed before schedule. 

    7. TALUKA RANKING – No 1 in 70% of Taluka in H1FY25 vs 66% in H1FY24. No 1+2 in 85% vs 81% LY 

    8.UBS – 233 outlets in Q2 vs budget of 180. YoY Growth in Birla Pivot 38% and UTCL brands 24.8% 

    9. Fuel cost better in Q2FY25 at Rs 1,858/Mkcal vs LE of Rs 1,930/Mkcal – due to optimized use to Petcoke 
    

  **
               
  Extract these kinds of points from the document mentioned .
  Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.            
               """,
               
  "page_2" : """  
      You are a points extractor from the documents mentioned.
      These are the points which you needs to extract :
      
      B. UBS
        1. Added 233 new stores in Q2FY25 (85 in Q1FY25) vs budget of 180 stores. 64% outlet in rural. 

        2. Sharp degrowth in retail cement sale of Express stores (-8.8% Urban, -16.3% Rural). Outlook? (Slide 7B) 
        
        3. Provide key KPIs in table which will also covers different quarters information.(Provide table for this section)
        
        4. Sales performance trend (Provide reasons and a table for the trend)
        
        Extract these kinds of points from the document mentioned .
        Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  """,
  
  "page_3" : """  
      You are a points extractor from the documents mentioned.
      These are the points which you needs to extract :
      
      c. OPERATIONS 
        1. VARIABLE COST (Slide 45): Lower by Rs 5.5/b vs budget 
          - Raw Material Rs 16.32/b in Q2FY25 lower vs budget Rs 17.3/b – due to lower cost of limestone and raw mix optimization. Learnings? Permanent savings?  

          - Additives – though lower vs budget but sharp increase in last 3 years; up by almost 38%. Reasons? 

          - Q2 LE variable cost (slide 18) – Rs 118.3/b vs 105/b in Q1 – whereas fuel cost Rs 1,930/Mkcal in Q2 LE vs Rs 2018/Mkcal (additional slide). Understand?  

          - Increase in Power cost by Rs 0.8/b vs Q1 whereas Power cost has come down from Rs 5.7/kwh in Q1 to Rs 5.5/Kwh in Q2 – Reason? (Slide 45, 19B) 

          - Stores and Spares – Rs 5.95/b v budget Rs 7.04/b 
          
          - Non availability of manpower for shutdown and projects – BRC suggested to maintain a crew given the increasing scale of operations 
          
          Create a quarterwise table for this section if possible
          

        2. Fuel Mix: 
          - Indigenous coal expected to decline in Q3 to 6.1% from 9.1% in Q2 – due to fixed contracts? (slide 18B) 

          - Reason for increase in AFR cost in Q3LE to Rs 1245/Mkcal from Rs 1197/Mkcal in Q2 (FY24 Rs 1073/Mkcal) – Reason?  

          - Reason for higher cost of captive mines Rs 2930 /MKcal in Q2FY25 vs budget Rs 2510/Mkcal (Rs 2817/Mkcal in Q1FY25) ? 
          
          **Create a quarter-wise table for this section if possible**

       
        Extract these kinds of points from the document mentioned .
        Keep the Nested points properly in markdown format, points should be under a h4 with proper heading if needed.
  """
               
   
                    }