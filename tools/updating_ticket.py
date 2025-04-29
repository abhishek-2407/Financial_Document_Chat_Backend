

import datetime
from langchain_core.tools import tool
from utils.postgres_connection import ConnectDB

@tool
def update_ticket(solution: str , ticket_id : str ):
    """
    Marks a customer support ticket as resolved by updating the resolution status,
    solution text, and the date of resolution in the database.

    Parameters:
    ----------
    solution : str
        A brief explanation or description of the solution provided for the issue.

    ticket_id : str
        The UUID of the support ticket that needs to be updated.

    Returns:
    -------
    dict
        A dictionary containing:
        - status (int): HTTP-style status code (200 for success).
        - response (str): A message indicating whether the ticket was successfully marked as resolved
          or if escalation to a human agent is needed.
    """
    
    try:
        db = ConnectDB()
        sql_query = [{
            "query" : """UPDATE customer_support_tickets
                            SET resolution_status = 'resolved', solution = %s, date_of_resolution = CURRENT_TIMESTAMP
                            WHERE ticket_id = %s;""" ,
            "data" : (solution,ticket_id)
        }]
        
        response = db.update(sql_query)
        
        if response["status_code"] == 200:
            return {
                "status_code" : 200,
                "response"  : "Ticket is marked resolved for the issue"
            }
        
        else :
            return {
                "status_code" : 200,
                "response"  : "Failed to resolve this issue, we are setting up an call with the our human agent to resolve the issue. Thanks for your patience."
            }
            
    finally:
        db.close_connection()
            
    
        
        
    
        
        