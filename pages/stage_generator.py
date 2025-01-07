import requests
from datetime import datetime, timezone, timedelta
import streamlit as st
import json

url  = 'https://www.heywhale.com/admin/v2/api/stages'

def generate_time_string(year,month,day, hour, minute, second):
    '''
    Generate a string in the format "YYYY-MM-DDTHH:MM:SS.000Z" 
    The inputs are from Asia/Shanghai timezone.
    Convert the inputs to UTC timezone
    '''
    shanghai_tz = timezone(timedelta(hours=8))
    dt_shanghai = datetime(year, month, day, hour, minute, second, tzinfo=shanghai_tz)
    
    # Convert to UTC timezone
    dt_utc = dt_shanghai.astimezone(timezone.utc)
    
    # Format the datetime as a string in UTC
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def create_stage(stage_name, start_datetime, end_datetime, award, competition_id, cookies):
    data = {"Name": stage_name,
            "StartDate": start_datetime,
            "EndDate": end_datetime,
            "GroupSync": False,
            "NeedAgreement": False,
            "AgreementFields": [],
            "AuthorizeNotice": "",
            "AuthorizationLock": False,
            "AwardWhaleCoin": award,
            "Competition": competition_id}
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=data, cookies=cookies)
    return response


st.title('批量生成活动阶段')

competition_id = st.text_input('Competition ID')
num_stages = st.number_input('Number of Stages (n)', min_value=1, value=1, step=1)
start_datetime = st.text_input(label='Start Datetime', value=generate_time_string(2025, 1, 3, 16, 0, 0))
end_datetime = st.text_input(label='End Datetime', value=generate_time_string(2025, 1, 7, 16, 0, 0))
cookie_string = st.text_area('Cookie', help='Copy the cookie from your browser. e.g.: kesci.client_sig=...; heywhale.sid.v2=...; heywhale.sid.v2.sig=...', placeholder='kesci.client_sig=...; heywhale.sid.v2=...; heywhale.sid.v2.sig=...')


if st.button('Create Stages'):
    
    if not competition_id:
        st.error('Please input Competition ID.')
    elif not cookie_string:
        st.error('Please input Cookie.')
    else:
        try:
            # Parse the cookie string into a dictionary
            cookies = {}
            for item in cookie_string.split(';'):
                item = item.strip()
                if not item:
                    continue
                key, value = item.split('=', 1)
                cookies[key] = value
                
            
            for i in range(1, num_stages + 1):
                stage_name = f"关卡 {i}"
                if i <= 2:
                    award = 1
                elif i < num_stages:
                    award = i - 1
                elif i == num_stages:
                    award = 6
                else:
                  raise ValueError("Invalid stage number")
                
                response = create_stage(stage_name, start_datetime, end_datetime, award, competition_id, cookies)
                
                if response.status_code == 200:
                    st.success(f"Stage '{stage_name}' created successfully! Award: {award}. Response: {response.json()}")
                else:
                    st.error(f"Failed to create stage '{stage_name}'. Status code: {response.status_code}. Response: {response.text}")

        except ValueError as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"An error occurred: {e}")