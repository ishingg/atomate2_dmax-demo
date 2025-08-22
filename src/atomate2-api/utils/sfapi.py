from sfapi_client import AsyncClient
from sfapi_client.compute import Machine
from sfapi_client import Resource
from authlib.jose import JsonWebKey
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc7523 import PrivateKeyJWT
from dotenv import load_dotenv
from io import BytesIO
from .preprocessing import generate_hash
import asyncio
import json
import os
import time




# Load environment variables from .env file
load_dotenv()

# Get the credentials from the environment
client_id = os.getenv("SFAPI_CLIENT_ID")
sfapi_secret = os.getenv("SFAPI_SECRET")
private_key= os.getenv("SFAPI_PRIVATE_KEY")
client_secret = JsonWebKey.import_key(json.loads(sfapi_secret))

# Create authenticated session
token_url = "https://oidc.nersc.gov/c2id/token"
session = OAuth2Session(
    client_id, 
    private_key, 
    PrivateKeyJWT(token_url),
    grant_type="client_credentials",
    token_endpoint=token_url
)
session.fetch_token()

async def fetch_status():
    """Fetch and print the status of the Perlmutter machine."""
    async with AsyncClient() as client:
        status = await client.compute(Machine.perlmutter)
        print("Checking Perlmutter Status:")
        print(status)
        print()

async def get_status():
    """Get the status of the Perlmutter machine using credentials."""
    async with AsyncClient(client_id, client_secret) as client:
        perlmutter = await client.compute(Machine.perlmutter)
        print(f"Checking Perlmutter Connection: {perlmutter.description}")
        return {
            "machine_name" : perlmutter.full_name,
            "description": perlmutter.description,
            "status": perlmutter.status,
            "system_type": perlmutter.system_type
        }

async def fetch_outages():
    """Fetch and print the most recent outages for the Spin resource."""
    async with AsyncClient() as client:
        outages = await client.resources.outages(Resource.spin)
        print("Recent Outages for Spin:")
        if outages:
            for outage in outages:
                print(outage)
        else:
            print("No recent outages found.")
        print()

async def upload_file(file_path, target_directory):
    """Upload a file to a specified directory on Perlmutter."""
    async with AsyncClient(client_id, client_secret) as client:
        perlmutter = await client.compute(Machine.perlmutter)

        # List directories to find the target directory
        directories = await perlmutter.ls(target_directory, directory=True)
        if not directories:
            print(f"Directory {target_directory} does not exist on Perlmutter.")
            return

        # Assuming target_directory is valid, proceed with upload
        [target] = directories

        # Open the file as a binary stream
        with open(file_path, "rb") as f:
            file_content = BytesIO(f.read())
            file_content.filename = os.path.basename(file_path)  # Set the filename attribute

            await target.upload(file_content)
            print(f"Uploaded {file_path} to {target_directory} on Perlmutter.")

def create_directory_on_login_node(system_name, root_directory, directory_name=generate_hash()):
    """Create a directory in Perlmutter login node by running a mkdir command."""
    
    # Construct the new directory path
    new_directory_path = f"{root_directory}/{directory_name}"

    # Construct the command to make the directory
    cmd = f"mkdir -p {root_directory}/{directory_name}"

    # Define the API endpoint
    api_endpoint = f"https://api.nersc.gov/api/v1.2/utilities/command/{system_name}"

    # Send the POST request with the command
    response = session.post(api_endpoint, data={"executable": cmd})

    # Check if the request was successful
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get('status') == 'OK':

            # Print response from GET tasks
            task_id = response_data.get('task_id')
            task_endpoint = f"https://api.nersc.gov/api/v1.2/tasks/{task_id}"
                
            # Send the GET request with the command
            r = session.get(task_endpoint)
            time.sleep(1) # Perlmutter needs a second to make the directory else this endpoint will throw 500 without a buffer 

            print(f"Directory {new_directory_path} created successfully.")
            return new_directory_path
        else:
            print(f"Failed to create directory: {response_data.get('error')}")
            return None
    else:
        print(f"HTTP request failed with status code: {response.status_code}")
        return None

def cat_file(file_dir, file_name):
    """Cat the file in Perlmutter login node by running a cat command."""
    
    # Construct the command to cat the file
    cmd = f'cat {file_dir}/{file_name}'

    # Define the API endpoint
    command_endpoint = "https://api.nersc.gov/api/v1.2/utilities/command/perlmutter"

    # Send the POST request with the cat command
    cat_response = session.post(command_endpoint, data={"executable": cmd})

    # Check if the request was successful
    if cat_response.status_code == 200:
        cat_response_data = cat_response.json()
        if cat_response_data.get('status') == 'OK':
            return cat_response_data
        else:
            print(f"Failed to cat file: {cat_response.get('error')}")
            return None
    else:
        print(f"HTTP request failed with status code: {cat_response.status_code}")
        return None
    
def remove_file(file_dir, file_name):
    """Remove the file in Perlmutter login node by running a rm command."""
    
    # Construct the command to cat the file
    cmd = f'rm {file_dir}/{file_name}'

    # Define the API endpoint
    command_endpoint = "https://api.nersc.gov/api/v1.2/utilities/command/perlmutter"

    # Send the POST request with the cat command
    rm_response = session.post(command_endpoint, data={"executable": cmd})

    # Check if the request was successful
    if rm_response.status_code == 200:
        rm_response_data = rm_response.json()
        if rm_response_data.get('status') == 'OK':
            return rm_response_data
        else:
            print(f"Failed to remove file: {rm_response.get('error')}")
            return None
    else:
        print(f"HTTP request failed with status code: {rm_response.status_code}")
        return None
    
def recursively_rm_dir(dir_to_rm):
    """Remove a directory in Perlmutter login node by running a rm -r command."""
    
    # Construct the command to cat the file
    cmd = f'rm -r {dir_to_rm}'

    # Define the API endpoint
    command_endpoint = "https://api.nersc.gov/api/v1.2/utilities/command/perlmutter"

    # Send the POST request with the cat command
    rm_response = session.post(command_endpoint, data={"executable": cmd})

    # Check if the request was successful
    if rm_response.status_code == 200:
        rm_response_data = rm_response.json()
        if rm_response_data.get('status') == 'OK':
            return rm_response_data
        else:
            print(f"Failed to remove directory recursively: {rm_response.get('error')}")
            return None
    else:
        print(f"HTTP request failed with status code: {rm_response.status_code}")
        return None

def get_task(task_id, max_retries=10, delay=5):
    """Fetches task details from SFAPI and retries if status is 'new'."""
    task_endpoint = f"https://api.nersc.gov/api/v1.2/tasks/{task_id}"

    for attempt in range(max_retries):
        # Send the GET request
        task_response = session.get(task_endpoint)
        print(f"[INFO] Attempt {attempt + 1}/{max_retries}: Checking task {task_id}")

        if task_response.status_code == 200:
            task_data = task_response.json()
            task_status = task_data.get("status", "").lower()

            # Handle 'new' status - retry logic
            if task_status == "new":
                print(f"[INFO] Task {task_id} is still in 'new' state. Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(delay)  # Wait before retrying
                continue

            # Handle 'completed' or 'ok' status
            if task_status in ["completed", "ok"] and "result" in task_data:
                return task_data

            # Handle unexpected status
            print(f"[ERROR] Task {task_id} has an unexpected status: {task_status}")
            return {"error": f"Task status '{task_status}' is not valid."}, 404

        else:
            print(f"[ERROR] HTTP request failed with status code: {task_response.status_code}")
            return {"error": f"Request failed with status code {task_response.status_code}"}, 500

    # If we reach here, max retries were exhausted
    return {"error": f"Task {task_id} is still in 'new' state after {max_retries} retries."}, 408


def get_all_lpad_wflows():
    """Get the launchpad's workflows in Perlmutter login node by runnng command from SFAPI."""

    # Construct the command to activate the environment and get the workflows
    wflows_cmd = 'lpad get_wflows'

    # Define the API endpoint
    command_endpoint = "https://api.nersc.gov/api/v1.2/utilities/command/perlmutter"

    # Send the POST request with the command
    wflows_response = session.post(command_endpoint, data={"executable": wflows_cmd})

    # Check if the request was successful
    if wflows_response.status_code == 200:
        response_data = wflows_response.json()
        if response_data.get('status') == 'OK':
            return response_data # Return successful response

        else:
            error_message = response_data.get('error', 'Unknown error occurred')
            print(f"[ERROR] Failed to get lpad wflows: {error_message}")
            return {"error": error_message}  # JSON error response for Postman
    
    elif wflows_response.status_code == 403:
        print("[ERROR] Authentication failed: SFAPI token has likely expired.")
        return {"error": "Authentication failed. Your SFAPI token may have expired. Please reauthenticate."}

    else:
        print(f"[ERROR] HTTP request failed with status code: {wflows_response.status_code}")
        return {"error": f"Request failed with status code {wflows_response.status_code}"}


def run_worker_step(worker_step, workflow_id):
    """Call worker step scripts (generate, run, write) on NERSC via sfapi's run command"""
    print(f"Running run_worker_step with {worker_step} for {workflow_id}")

    # Construct the command to call the worker step script
    root_dir = os.getenv("ROOT_DIR")
    worker_dir = root_dir + "/src/FFForge/api/nersc/ffforge/" +worker_step+".py"
    workflow_dir = root_dir + "/workflows/" + workflow_id
    cmd = f'python {worker_dir} {workflow_dir}'

    # Define the API endpoint
    command_endpoint = "https://api.nersc.gov/api/v1.2/utilities/command/perlmutter"

    # Send the POST request with the step command
    step_response = session.post(command_endpoint, data={"executable": cmd})

    # Check if the request was successful
    if step_response.status_code == 200:
        step_response_data = step_response.json()
        if step_response_data.get('status') == 'OK':
            print(step_response_data)
            return step_response_data
        else:
            print(f"Failed to run worker step: {step_response.get('error')}")
            return None
    else:
        print(f"HTTP request failed with status code: {step_response.status_code}")
        return None
    
def get_lpad_wf(workflow_id, query_filter):
    """Get a workflow with Perlmutter login node by running command from SFAPI."""

    # Construct the command to get the workflow by the query
    lpad_cmd = f'lpad get_fws_in_wflows -wfq \'{{"metadata.workflow_id": "{workflow_id}"}}\' {query_filter}'

    # Define the API endpoint
    command_endpoint = "https://api.nersc.gov/api/v1.2/utilities/command/perlmutter"

    # Send the POST request with the command
    lpad_response = session.post(command_endpoint, data={"executable": lpad_cmd})

    # Check if the request was successful
    if lpad_response.status_code == 200:
        response_data = lpad_response.json()

        # Check if command execution was successful
        if response_data.get('status') == 'completed':
            # Extract the raw output from the response
            raw_output = response_data.get('result', {}).get('output', "")

            try:
                # Parse the raw JSON string from the "output"
                parsed_output = json.loads(raw_output)
                print("[INFO] Workflow details fetched successfully:", parsed_output)
                return parsed_output  # Return the parsed JSON

            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse workflow output: {str(e)}")
                return {"error": "Failed to parse workflow output."}
        elif response_data.get('status') == 'OK':
            print("[INFO] Workflow task fetched successfully:", response_data)
            return response_data
        else:
            error_message = response_data.get('error', 'Unknown error occurred')
            print(f"[ERROR] Failed to get lpad wflows: {error_message}")
            return {"error": error_message}  # JSON error response
    
    elif lpad_response.status_code == 403:
        print("[ERROR] Authentication failed: SFAPI token has likely expired.")
        return {"error": "Authentication failed. Your SFAPI token may have expired. Please reauthenticate."}

    else:
        print(f"[ERROR] HTTP request failed with status code: {lpad_response.status_code}")
        return {"error": f"Request failed with status code {lpad_response.status_code}"}