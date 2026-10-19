import json
from pathlib import Path

# get valid data which accepted in validation layer from "final_dataset_report.json" file
def get_valid_dataset_paths(report_path="assets/reports/final_dataset_report.json"):
    path= Path(report_path)

    if not path.exists():
        PermissionError(f"Error: Report file not found at {path}")
        return{}
    with open(path, "r",encoding="utf-8" ) as f:
        data = json.load(f)

        # Extract the 'clean_dataset' section from the structure contained in the file
        clean_dataset = data.get("clean_dataset", {})

        # small report to accepted classes
        print("=" * 50)
        print(" Valid Dataset Summary from Report:")
        print("=" * 50)
        total_images = 0
        for class_name, image_paths in clean_dataset.items():
            count = len(image_paths)
            total_images += count
            print(f" - Class `{class_name}`: {count} valid images")
        print("=" * 50)
        print(f" Total Valid Images across all classes: {total_images}")
        print("=" * 50)

        return clean_dataset

'''
===============
clean_dataset 
====================================================================================================== 
{
    "Healthy": [
        "D:\\primary_projects\\grad_cs_sha\\implementation\\demo\\data\\Healthy\\healthy (1).jpeg",
        "D:\\primary_projects\\grad_cs_sha\\implementation\\demo\\data\\Healthy\\healthy (2).jpeg"
        # ... and all other validated healthy images
    ],
    "Mosaic": [
        "D:\\primary_projects\\grad_cs_sha\\implementation\\demo\\data\\Mosaic\\mosaic (1).jpeg",
        "D:\\primary_projects\\grad_cs_sha\\implementation\\demo\\data\\Mosaic\\mosaic (2).jpeg"
        # ... and all other validated mosaic images
    ]
}
====================================================================================================== 
'''

if __name__ == "__main__":
    valid_data = get_valid_dataset_paths()
    
    # Example: Accessing images of a specific class and printing only the first 3 paths

    if "Healthy" in valid_data:
        print("\nExample - First 3 healthy image paths:")
        for img_path in valid_data["Healthy"][:3]:
            print(img_path)


    