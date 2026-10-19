import os
import json 
from pathlib import Path
from src.layer_one_validation_layer.phase_1_files_validation.first_check_one_image.check_image import(
    analyze_and_validate_classes,
    verify_images_deep_integrity,
    verfiy_images_size,
    verify_images_resolution,
    verify_images_aspect_ratio,
    verify_images_pixel_variation
)

from src.layer_one_validation_layer.phase_1_files_validation.second_check_all_images.check_all_images import (
    load_classes,
    find_class_images,
    validate_image,
    detect_exact_duplicates,
    detect_visual_similarity,
    validate_class_counts,
    CONFIG_PATH,
    valid_images
)

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


def run_full_pipeline():
    print("=" * 65)
    print("      DATASET SETUP & FULL VALIDATION PIPELINE     ")
    print("=" * 65)

    # Read Classes and save it 
    print("\n[Step 1] Configuring classes and generating config file...")
    stored_dirs = get_class_directories()
    
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_path)
    target_folder = os.path.join(project_root, "assets")
    config_filepath = os.path.join(target_folder, "classes_config.json")

    os.makedirs(target_folder, exist_ok=True)
    with open(config_filepath, "w", encoding="utf-8") as f:
        json.dump(stored_dirs, f, indent=4)

    print(f"\n--- Stored Class Directories Saved Successfully to: ---\n{config_filepath}\n")

    # Check image by image Phase 1 part 1
    print("[Step 2] Running 6-Layer Individual Image Validation...")
    passed_layer1 = analyze_and_validate_classes()
    if not passed_layer1:
        print(" Pipeline stopped: No classes passed Layer 1.")
        return

    passed_layer2 = verify_images_deep_integrity(passed_layer1)
    if not passed_layer2:
        print(" Pipeline stopped: No classes passed Deep Integrity.")
        return

    passed_layer3 = verfiy_images_size(passed_layer2)
    if not passed_layer3:
        print(" Pipeline stopped: No classes passed Size Check.")
        return

    passed_layer4 = verify_images_resolution(passed_layer3)
    if not passed_layer4:
        print(" Pipeline stopped: No classes passed Resolution Check.")
        return

    passed_layer5 = verify_images_aspect_ratio(passed_layer4)
    if not passed_layer5:
        print(" Pipeline stopped: No classes passed Aspect Ratio Check.")
        return

    final_clean_dict = verify_images_pixel_variation(passed_layer5)
    print("\n Individual validation checks completed successfully.")

    # Check all images "Advanced checking"
    print("\n[Step 3] Running Advanced Dataset Checks (Duplicates & pHash)...")
    try:
        classes = load_classes(CONFIG_PATH)
        images_by_class = find_class_images(classes)

        for class_name, paths in images_by_class.items():
            for path in paths:
                if str(path) in [str(p) for sublist in final_clean_dict.values() for p in sublist]:
                    validate_image(path, class_name)

        duplicate_groups = detect_exact_duplicates(valid_images)
        similar_pairs = detect_visual_similarity(valid_images)
        class_counts = validate_class_counts(images_by_class)
        print("\n Advanced checks completed.")

    except Exception as e:
        print(f"Warning during advanced checks: {e}")

    # Final REport
    reports_dir = Path(project_root) / "assets" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    final_report_path = reports_dir / "final_dataset_report.json"

    serializable_dict = {
        class_name: [str(p) for p in paths] 
        for class_name, paths in final_clean_dict.items()
    }

    payload = {
        "status": "SUCCESS",
        "clean_dataset": serializable_dict
    }

    with open(final_report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)

    print("\n" + "=" * 65)
    print(f" FULL PIPELINE FINISHED SUCCESSFULLY!")
    print(f" Final clean dataset report saved to: {final_report_path}")
    print("=" * 65)

if __name__ == "__main__":
    run_full_pipeline()