from flask import Flask, request
from flask_restful import Resource
from pathlib import Path
from dmax.flows.core import BaseDataGenerationFlow
from dmax.models.workflowmodel import create_workflow_entry  # Import model function
#from utils.sfapi import upload_file, create_directory_on_login_node, get_status, cat_file, get_task, get_all_lpad_wflows, remove_file, recursively_rm_dir, run_worker_step, get_lpad_wf
from bson.objectid import ObjectId
import os
import subprocess
import asyncio
import numpy as np
import json
from dotenv import load_dotenv
import time
from __init__ import api
import os 
#for my own enrichment
#the routes file essentially is the place to put all API endpoints that come 
#from the front end 
#each class represents an endpoint
#mongodb still needs to be established for DMAx


load_dotenv()


class demoTest(Resource):

    def get(self):
        return {'demo_gen': 'welcome to demo test'}

    def post(self):
        # Get JSON data from frontend or Postman
        

        # Example processing
        
        
        BaseDataGenerationMaker = BaseDataGenerationFlow()
        
        DataGenerationFlow = BaseDataGenerationMaker.make(
            smiles = request.form.get("smiles"),
            left_cap = request.form.get("left_cap"),
            right_cap = request.form.get("right_cap"),
            length = request.form.get("length"),
            num_molecules = request.form.get("num_molecules"),
            density = request.form.get("density"),
            box_type = request.form.get("box_type"),
            num_conf = request.form.get("num_conf"),
            loop = request.form.get("loop")
        )
        
        response = {
            "status": "success",
            "received": {
                
            }
        }
        print("Sending Response:", json.dumps(response))
        return response, 200
    
class DataGenerationSubmission(Resource):
    def post(self):
        #initialize variables to upload fields to perlmutter and MongoDB
        structure_file_path = None
        json_file_path = None
        
        try:    
            # Extract form data (or use request.get_json() for JSON)
            form_fields = [
                "name", "smiles", "left_cap", "right_cap", "length", "num_molecules",
                "density", "box_type", "out_dir", "num_conf", "loop"
            ]
            
            #uploading workflow to mongoDB 
            # Create workflow entry
            workflow_entry = create_workflow_entry(form_fields)
            #change to the db name when db is created 
            workflow_id = workflow_entry.get("name")
            #workflow_id = workflows_collection.insert_one(workflow_entry).inserted_id

            # Ensure a file is uploaded
            if 'structure_file' not in request.files or request.files['structure_file'].filename == '':
                return {'error': 'A structure file is required for this workflow submission.'}, 400
            structure_file = request.files.get('structure_file')

            # Create 'static' directory if it doesn't exist
            if not os.path.exists('static'):
                os.makedirs('static')
                    
            original_filename = structure_file.filename
            prefix = os.path.splitext(original_filename)[0]
            extension = os.path.splitext(original_filename)[1]

            # Use workflow_id as name of directory to put file in
            workflow_dir_name = str(workflow_id)
            
            
            #upload workflow Perlmutter 
            

            # Create a directory in Perlmutter
            root_dir = os.getenv("ROOT_DIR")
            if not root_dir:
                raise EnvironmentError("ROOT_DIR environment variable not set.")
                
            new_directory = create_directory_on_login_node("perlmutter", root_dir + "/workflows", workflow_dir_name)            
            if not new_directory:
                return {'error': "Failed to create directory on Perlmutter."}, 500

            # Construct the new structure file name
            new_filename = f"{prefix}_{workflow_id}{extension}"
            structure_file_path = os.path.join('static', new_filename)
            structure_file.save(structure_file_path) # Save the structure file locally

            # Create JSON file containing workflow specifications
            json_filename = f"wf_specifications_{prefix}_{workflow_id}.json"
            json_file_path = os.path.join('static', json_filename)


            # Base specification
            wf_specification = {
                "name": request.form.get("name"),
                "smiles": request.form.get("smiles"),
                "left_cap": request.form.get("left_cap"),
                "right_cap": request.form.get("right_cap"),
                "length": request.form.get("length"),
                "num_molecules": request.form.get("num_molecules"),
                "density": request.form.get("density"),
                "box_type": request.form.get("box_type"),
                "out_dir": request.form.get("out_dir"),
                "num_conf": request.form.get("num_conf"),
                "loop": request.form.get("loop"),
                "structure_filename": new_filename  # Store reference to the structure file
            }
            
            # Write JSON data to file
            with open(json_file_path, 'w') as json_file:
                json.dump(wf_specification, json_file, indent=4)

            # Upload files to Perlmutter
            try:
                asyncio.run(upload_file(structure_file_path, new_directory)) # Upload structure file
                asyncio.run(upload_file(json_file_path, new_directory)) # Upload workflow specification file
            except Exception as e:
                return {'error': f"Failed to upload files to Perlmutter: {str(e)}"}, 500
                
            
            
            received = {field: request.form.get(field) for field in form_fields}
            # Placeholder response
            return {    
                "status": "success",
                "message": "Stub: received web-form submission.",
                "received_data": received
            }, 200
            
        except Exception as e:
            return {"error": str(e)}, 400  # HTTP 400 Bad Request
        
        finally:
            # Remove local files if they exist
            if structure_file_path and os.path.exists(structure_file_path):
                os.remove(structure_file_path)
            if json_file_path and os.path.exists(json_file_path):
                os.remove(json_file_path)
            
            # Start a fetcher for this workflow
            # run_fetcher(workflow_id)
        
# Route for DMAx Submission (placeholder)
class DMAxInput(Resource):
    def get(self):
        return {'text': 'welcome to dmax workflow submission page', 'test-text':'H2o'}
    
    def post(self):
        # TODO 
        
        json_file_path = None
        
        try:
            #create new dictionary for data 
            data = {
                "smiles": request.form.get('smilesString'),
                "name": request.form.get('name'),
                "left_cap": request.form.get('leftCap'),
                "right_cap": request.form.get('rightCap'),
                "polymer_length": request.form.get('polymerLength'),
                "number_molecules": request.form.get('numberMolecules'),
                "density": request.form.get('density')
            }
            
            #create wf on mongodb i think?
            workflow_entry = {
                "smiles": data["smiles"],
                "name": data["name"],
                "left_cap": data["left_cap"],
                "right_cap": data["right_cap"],
                "polymer_length": data["polymer_length"],
                "number_molecules": data["number_molecules"],
                "density": data["density"]
            }
            workflow_id = workflows_collection.insert_one(workflow_entry).inserted_id
            
            #get info for naming later
            workflow_dir_name = str(workflow_id)
            name = data['name']
            
            # Create a directory in Perlmutter 
            root_dir = os.getenv("ROOT_DIR")
            if not root_dir:
                raise EnvironmentError("ROOT_DIR environment variable not set.")
            
            #create new directory for each wf
            new_directory = create_directory_on_login_node("perlmutter", root_dir + "/dmax_submissions", workflow_dir_name)            
            if not new_directory:
                return {'error': "Failed to create directory on Perlmutter."}, 500  
            
            # Create JSON file containing workflow specifications
            json_filename = f"{name}_{workflow_id}.json" 
            json_file_path = os.path.join('static', json_filename)
            
            wf_specification = {
                "workflow_id": str(workflow_id),
                "smiles": data["smiles"],
                "name": data["name"],
                "left_cap": data["left_cap"],
                "right_cap": data["right_cap"],
                "polymer_length": data["polymer_length"],
                "number_molecules": data["number_molecules"],
                "density": data["density"]
            }          

            with open(json_file_path, 'w') as json_file:
                json.dump(wf_specification, json_file, indent=4)
                
            #upload 
            try:
                asyncio.run(upload_file(json_file_path, new_directory)) # Upload workflow specification file

            except Exception as e:
                return {'error': f"Failed to upload files to Perlmutter: {str(e)}"}, 500
                
            # Update mongoDB wf entry
            new_status = "generating runs"
            # update_workflow_status(new_status, str(workflow_id))
            
            #print for error handling

            # Access request form data
            smiles = request.form.get('smilesString')
            name = request.form.get('name')
            left_cap = request.form.get('leftCap')
            right_cap = request.form.get('rightCap')
            polymer_length = request.form.get('polymerLength')
            number_molecules = request.form.get('numberMolecules')
            density = request.form.get('density')

            # Log to console for debugging
            print("Received SMILES string: " + smiles)
            print("Received name: " + name)
            print("Received left cap: " + left_cap)
            print("Received right cap: " + right_cap)
            print("Received polymer length: " + polymer_length)
            print("Received number of molecules: " + number_molecules)
            print("Received density: " + density)
            

            return {
                "message": "Workflow submitted and files uploaded successfully!",
                "workflow_id": str(workflow_id),
            }, 201  # HTTP 201 Created

        except Exception as e:
            return {"error": str(e)}, 400  # HTTP 400 Bad Request
        
        finally:
            # Remove local files if they exist
            if json_file_path and os.path.exists(json_file_path):
                os.remove(json_file_path)
            
            # Start a fetcher for this workflow
            # run_fetcher(workflow_id) 
            
        return {
            'smilesString': smiles 
        }      
        

api.add_resource(DataGenerationSubmission, "/atomate2-api/dmax-input/")
api.add_resource(demoTest, "/atomate2-api/process/")
