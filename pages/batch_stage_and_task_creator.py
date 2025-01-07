import requests
from datetime import datetime, timezone, timedelta
import streamlit as st
import json
import random
import string
import io
import uuid
from requests_toolbelt import MultipartEncoder

# --- Helper Functions ---
def generate_random_string(length=10):
    """生成指定长度的随机字符串"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_time_string(year, month, day, hour, minute, second):
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

# 上传文件到七牛云
def upload_file_to_qiniu(token, key, file):
    """上传文件到七牛云"""
    file_stream = io.BytesIO(file.getvalue())
    boundary = uuid.uuid4().hex
    multipart_data = MultipartEncoder(
        fields={
            'token': token,
            'key': key,
            'file': (file.name, file_stream, 'application/octet-stream')
        },
        boundary = boundary
    )
    response = requests.post(
        url='https://up.qbox.me/',
        data=multipart_data,
        headers={'Content-Type': multipart_data.content_type}
    )
    response.raise_for_status()  # 如果请求失败，抛出异常
    return response.json()
# --- API Functions ---
def create_stage(stage_name, start_datetime, end_datetime, award, competition_id, cookies):
    url  = 'https://www.heywhale.com/admin/v2/api/stages'
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
    try:
        response = requests.post(url, headers=headers, json=data, cookies=cookies)
        response.raise_for_status()  # 如果请求失败，抛出异常
        return response
    except requests.exceptions.ConnectionError as e:
          raise Exception(f"Network connection error: {e}")
    except requests.exceptions.Timeout as e:
          raise Exception(f"Request timeout error: {e}")
    except Exception as e:
          raise Exception(f"An unexpected error occurred: {e}")

def create_task_and_upload_file(org_id, cookie_str, task_name, start_datetime, end_datetime, stage_id, submission_notice,
                                 review_daily_limit, answer_file, sample_file=None):
    """处理创建任务并上传文件的请求"""
    try:
        # 创建会话并设置头部
        session = requests.Session()
        session.headers.update({
            'x-kesci-org': org_id,
            'cookie': cookie_str
        })

        # 创建任务
        task_body = {
            "Name": task_name,
            "TaskType": "0",
            "StartDate": start_datetime,
            "EndDate": end_datetime,
            "SubmitDisabled": False,
            "AllowMemberSubmit": True,
            "ShowLeaderboard": True,
            "LeaderboardSortType": 0,
            "Normalization": False,
            "ShowPrivateLeaderboard": False,
            "ShowPrivateBestWork": False,
            "ObjectiveTaskInfo": {"SubmitType": "token", "AcceptExts": []},
            "Stage": stage_id
        }

        task_response = session.post("https://www.heywhale.com/admin/v2/api/tasks", json=task_body)
        if task_response.status_code != 200:
             raise Exception(f"Task creation failed: {task_response.text}")
        task_response.raise_for_status()
        task_data = task_response.json()
        task_id = task_data["document"]["_id"]

        # 获取上传文件的 token
        token_response = session.get("https://www.heywhale.com/api/uptoken?type=private")
        if token_response.status_code != 200:
             raise Exception(f"Failed to get uptoken: {token_response.text}")
        token_response.raise_for_status()
        upload_token = token_response.json().get('uptoken')

        # 上传答案文件
        random_file_name = generate_random_string()
        if "." in answer_file.name:
            answer_ext = answer_file.name.split(".")[-1]
        else:
            answer_ext = ""
        answer_key = f'tasks/{task_id}/answer/{random_file_name}.{answer_ext}'
        upload_file_to_qiniu(upload_token, answer_key, answer_file)


        # 上传示例文件
        sample_file_name = None
        sample_ext = None
        
        task_body.pop('TaskType')
        task_body.pop('Stage')
        # 更新任务信息
        task_update_body = {
            **task_body,
            "SubmissionNotice": submission_notice,
            "reviewAll": False,
            "ObjectiveTaskInfo": {
                "SubmitType": "token",
                "ReviewLimit": 0,
                "ReviewDailyLimit": review_daily_limit,
                "PublicAnswerFileName": answer_file.name,
                "PublicAnswerFileUrl": f"{random_file_name}.{answer_ext}",
                "AcceptExts": ["csv"],
                "ReviewLibs": [{"Lib": "60a0d35cca31cd0017836bfa", "Weight": 1, "ShowScoreDetail": True}]
            }
        }
        if sample_file:
            sample_file_name = generate_random_string()
            if "." in sample_file.name:
                 sample_ext = sample_file.name.split(".")[-1]
            else:
                  sample_ext = ""
            sample_key = f'tasks/{task_id}/sample/{sample_file_name}.{sample_ext}'
            upload_file_to_qiniu(upload_token, sample_key, sample_file)
            task_update_body['ObjectiveTaskInfo']['SampleFileName'] = sample_file.name
            task_update_body['ObjectiveTaskInfo']['SampleFileUrl'] = f'{sample_file_name}.{sample_ext}'
        # print(json.dumps(task_update_body))
        update_response = session.put(
            f'https://www.heywhale.com/admin/v2/api/tasks/{task_id}',
            json=task_update_body
        )
        if update_response.status_code != 200:
            raise Exception(f"Task update failed: {update_response.text}")
        update_response.raise_for_status()

        # 返回成功信息
        return {
            "msg": "Task created and file uploaded successfully",
            "id": task_id,
            "Name": task_name,
            "answer_file_name": answer_file.name,
            "sample_file_name": sample_file.name if sample_file else "" ,
            "sample_file_url": f'{sample_file_name}.{sample_ext}' if sample_file else ""
        }

    except requests.RequestException as e:
        return {"error": "External API error", "details": str(e)}, 500
    except Exception as e:
        return {"error": "Internal server error", "details": str(e)}, 500
# --- Streamlit App ---
def main():
    st.title('批量生成活动阶段、任务')
    
    # --- Input Fields ---
    cookie_string = st.text_area('Cookie', help='Copy the cookie from stages api. e.g.: kesci.client_sig=...; heywhale.sid.v2=...; heywhale.sid.v2.sig=...', placeholder='kesci.client_sig=...; heywhale.sid.v2=...; heywhale.sid.v2.sig=...')
    competition_id = st.text_input('Competition ID')
    org_id = st.text_input("Organization ID (Optional)", value="")
    
    # Use datetime.datetime.now() to calculate the default datetime strings
    now = datetime.now()
    start_datetime = st.text_input(label='Start Datetime', value=(now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    end_datetime = st.text_input(label='End Datetime', value=(now + timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    
    review_daily_limit = st.number_input("Review Daily Limit", min_value=0, value=10)
    submission_notice = st.text_area("Submission Notice (Markdown)", value="请认真提交，请勿作弊", height=150)

    create_option = st.radio("Create Options", options=["All Stages & Tasks", "Partial Stages & Tasks"])

    if create_option == "All Stages & Tasks":
        num_stages = st.number_input('Number of Stages (n_stage)', min_value=1, value=1, step=1)
        start_stage = 1
        end_stage = int(num_stages)
    else:
        start_stage = st.number_input("Start Stage Number (m)", min_value=1, value=2, step=1)
        end_stage = st.number_input("End Stage Number (n)", min_value=1, value=3, step=1)
        num_stages = end_stage - start_stage + 1

    answer_files = st.file_uploader("Upload CSV Answer Files", type=["csv"], accept_multiple_files=True)
    sample_files = st.file_uploader("Upload CSV Sample Files (Optional)", type=["csv"], accept_multiple_files=True)
    

    if st.button('Create Stages and Tasks'):
        
        if not competition_id:
            st.error('Please input Competition ID.')
        elif not cookie_string:
            st.error('Please input Cookie.')
        elif not answer_files:
           st.error('Please upload Answer Files.')
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
                
                #Strip the whitespace
                competition_id = competition_id.strip()
                org_id = org_id.strip()
                num_answer_files = len(answer_files)
                num_sample_files = len(sample_files) if sample_files else 0
                if num_answer_files != num_stages:
                  st.error("The number of answer files must match the number of stages.")
                  return
                if sample_files and num_sample_files != num_stages:
                    st.error("The number of sample files must match the number of stages.")
                    return

                # 对上传的文件列表进行排序
                answer_files = sorted(answer_files, key=lambda x: x.name)
                if sample_files:
                    sample_files = sorted(sample_files, key=lambda x: x.name)

                stages_ids = []
                with st.spinner(f'Creating {num_stages} Stages...'):
                   for i in range(start_stage, end_stage + 1):
                        stage_name = f"关卡 {i}"
                        if i <= 2:
                            award = 1
                        elif i < end_stage:
                            award = i - 1
                        elif i == end_stage:
                            award = 6
                        else:
                            raise ValueError("Invalid stage number")
                            
                        response = create_stage(stage_name, start_datetime, end_datetime, award, competition_id, cookies)
                            
                        if response.status_code == 200:
                            stage_id = response.json()['document']['_id']
                            stages_ids.append(stage_id)
                            st.success(f"Stage '{stage_name}' created successfully! Award: {award}, ID: {stage_id}")
                        else:
                            st.error(f"Failed to create stage '{stage_name}'. Status code: {response.status_code}. Response: {response.text}")
                            return  # Stop if stage creation fails

                # 将 cookies 字典转换为字符串
                cookie_str = "; ".join([f"{key}={value}" for key, value in cookies.items()])
                with st.spinner(f'Creating {num_stages} Tasks and Uploading Files...'):
                    for i, stage_num in enumerate(range(start_stage, end_stage + 1)):
                        task_name = f"关卡 {stage_num}"
                        sample_file = sample_files[i] if sample_files else None
                        try:
                             result = create_task_and_upload_file(
                                org_id,
                                cookie_str,
                                task_name,
                                start_datetime,
                                end_datetime,
                                stages_ids[i],
                                submission_notice,
                                int(review_daily_limit),
                                answer_files[i],
                                sample_file
                            )

                             if isinstance(result, tuple) and "error" in result[0]:
                                st.error(f"Error creating {task_name}: {result[0]['error']}, Details: {result[0]['details']}")
                             elif "error" in result:
                                 st.error(f"Error creating {task_name}: {result['error']}, Details: {result['details']}")
                             else:
                                st.success(f"{task_name} 已创建, 答案文件：{result['answer_file_name']}, 提交样例：{result['sample_file_name'] if result['sample_file_name'] else '无'}")
                                # if result['sample_file_name']:
                                #     st.write(f"提交样例文件地址：{result['sample_file_url']}")
                        except Exception as e:
                            st.error(f"Error creating {task_name}: {e}")
                    st.success(f"{num_stages} 个任务已全部创建成功，请核对 :)")
             except ValueError as e:
                st.error(f"Error: {e}")
             except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == '__main__':
    main()