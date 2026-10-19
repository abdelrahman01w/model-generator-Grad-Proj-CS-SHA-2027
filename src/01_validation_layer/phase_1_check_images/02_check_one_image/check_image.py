import os
import json
import cv2 as cv

def process_classes_dynamic():
    # get json and route for project

    current_script_path = os.path.dirname(os.path.abspath(__file__))  # --> D:\plant_disease_project\src
    project_route = current_script_path
    for _ in range(4):
        project_route = os.path.dirname(project_route)
        
    config_filepath = os.path.join(project_route, "assets", "classes_config.json")

    # check from json file , is it exist ?

    if not os.path.exists(config_filepath):
        print(f"Error: Config file not found at: {config_filepath}")
        print("Please run your setup script first to generate the directories configuration!")
        return

    # if it exist we will get classes which saved with directories in it
    with open(config_filepath , "r" , encoding="utf-8") as f:
        stored_dirs = json.load(f)

    if not stored_dirs:
        print("The configuration file is empty!")
        return
    # if we found classes
    print(f"Found {len(stored_dirs)} classes in the configuration file. Starting processing...\n")

    for class_name,class_path in stored_dirs.items():
        print(f"----------------------------------------")
        print(f"Accessing -> [{class_name}]")
        print(f"Path: {class_path}")
        print(f"----------------------------------------")

        if not os.path.isdir(class_path):
            print(f"Warning: The directory for {class_name} does not exist. Skipping.\n")
            continue
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
        image_files = [f for f in os.listdir(class_path) if f.lower().endswith(valid_extensions)]
        
        if not image_files:
            print(f"No images found inside {class_name}.\n")
            continue
        
        print(f"Found {len(image_files)} images. Getting image paths / reading...")

        # read each image 
        for filename in image_files:
            img_path = os.path.join(class_path, filename)
            
            # use it to read img using open cv
            # img = cv.imread(img_path)
            
            print(f"  -> Image: {img_path}")
            
        print("\n")

if __name__ == "__main__":
    process_classes_dynamic()