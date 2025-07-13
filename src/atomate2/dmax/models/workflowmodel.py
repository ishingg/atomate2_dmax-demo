from datetime import datetime, timezone

# Define the Workflow model as a dictionary (MongoDB is schema-less)
def create_workflow_entry(data):
    workflow_entry = {
        "name": data.get("name"),
        "smiles": data.get("smiles"),
        "left_cap": data.get("left_cap"),
        "right_cap": data.get("right_cap"),
        "length": data.get("length"),
        "num_molecules": data.get("num_molecules"),
        "density": data.get("density"),
        "box_type": data.get("box_type"),
        "out_dir": data.get("out_dir"),
        "num_conf": data.get("num_conf"),
        "loop": data.get("loop"),
        "created_at": datetime.now(timezone.utc)
    }
    return workflow_entry