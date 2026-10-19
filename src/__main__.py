import os
import json 
# Get classes from user 

def get_class_directories():
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_path)
    default_data_dir = os.path.join(project_root, "data")
    print(f"Project Root detected at: {project_root}")
    # I will use it to store all directoreis for all classes
    class_directories = {} # we will use it to track all directories 
    # after get number of classes no we will collect the directories in our dictionary

    entered_names = set()
    entered_paths = set()
    # Get the number of classes
    while True:
        try:
            num_classes = int(input("Hello Please enter the number of classes `Note : the minumum number of classes is 2 classes`: "))

            if num_classes > 1:
                break
            print("please enter 2 classes or")
        except ValueError:
            print("Invalid Input : please enter a vlid integer number")
    
    i=0
    while i < num_classes:
        print(f"\n--- Configuring Class {i + 1} of {num_classes} ---")
        class_name = input(f"Enter the name for class {i + 1}: ").strip()
        if not class_name:
            print("Error: Class name cannot be empty. Please enter a valid name.")
            continue
        if class_name in entered_names:
            print(f"Warning: The class name '{class_name}' is already entered! Please use a unique name.")
            continue
        suggested_path = os.path.join(default_data_dir, class_name)
        dir_path = input(f"Enter directory for class '{class_name}' [Default: {suggested_path}]: ").strip()        
        
        dir_path = dir_path.strip('"').strip("'") # to remove any quots in pathes

        if not dir_path:
            dir_path = suggested_path
            
        dir_path = dir_path.strip('"').strip("'")

        if not os.path.isdir(dir_path):
            print(f"Error : The directory `{dir_path}` doesn't exist. Please enter a valid path")
            continue
            
        if dir_path in entered_paths:
            print("Warning : you already entered this directory for another class!")
            continue

        # if user enter a valid path 
        entered_names.add(class_name)
        entered_paths.add(dir_path)
        class_directories[class_name] = dir_path
        i += 1
    return  class_directories      

    
if __name__ == "__main__":
    stored_dirs = get_class_directories()
    
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_path)
    target_folder = os.path.join(project_root, "assets")
    
    config_filepath = os.path.join(target_folder, "classes_config.json")

    os.makedirs(target_folder, exist_ok=True)

    with open(config_filepath, "w", encoding="utf-8") as f:
        json.dump(stored_dirs, f, indent=4)

    print(f"\n--- Stored Class Directories Saved Successfully to: ---\n{config_filepath}")

