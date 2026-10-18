import os
import json
import cv2 as cv
from collections import defaultdict

# Read all images

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
            img = cv.imread(img_path)
            
            print(f"  -> Image: {img_path}")
            
        print("\n")

# check Type for image and collect it
def analyze_and_count_img_extension(stored_dirs):
    '''
    A function to inspect all class folders, read the images,
    count the number of files for each format (extension), and tally the total.
    '''

    # dictionary to store number of image for each extension
    extension_count= defaultdict(int)

    # dictionary to store names of image for each extension
    extension_files = defaultdict(list)

    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

    print("=== Starting Image Extension Analysis ===\n")

    for class_name ,  class_path in stored_dirs.items():
        print(f" Scanning [{class_name}] at: {class_path}")

        # Check the path for class 
        if not os.path.isdir(class_path):
            print("Warning : Directory for {class_name} doesn't exist. Skipping.\n")
            continue

        # if we find exist path

        all_files = os.listdir(class_path) # get all images in class path

        for filename in all_files:

            img_path = os.path.join(class_path, filename)

            # after get one image we will check if it file or not
            if not os.path.isfile(img_path):
                continue

            # extract extension and convert it to small letter
            ext= os.path.splitext(filename)[1].lower()

            # check if this extension is accepted for our extensions 
            if ext in valid_extensions:
                # this optional to check the file if it afety or no "can read it"
                img= cv.imread(img_path)

                if img is not None:
                    extension_count[ext] += 1
                    extension_files[ext].append(filename)
                    print(f" -> Valid Image: { filename} [{ext}]")
                else:
                    print(f" -> Warning: File {filename} has extension {ext} but couldn't be read (corrupted?).")
            else:
                # if file is another extension which we accept it
                if ext: # do this to avoid files without extensions
                    extension_count["others/unknown"] += 1
                    print(f"  -> Other File Type: {filename} [{ext}]")
        print("=" * 40)
    print("\n========================================")
    print("       FINAL IMAGE EXTENSIONS REPORT    ")
    print("========================================")

    total_images = sum(extension_count.values())

    if total_images == 0:
        print("No valid images found across all classes.")
    else:
        for ext, count in extension_count.items():
            print(f"• Extension [{ext.upper()}]: {count} images")
        print("----------------------------------------")
        print(f"Total Valid Images Found: {total_images}")
        print("========================================")

    return extension_count, extension_files
if __name__ == "__main__":

    current_script_path = os.path.dirname(os.path.abspath(__file__))
    project_route = current_script_path
    for _ in range(4):
        project_route = os.path.dirname(project_route)

    config_filepath = os.path.join(project_route,"assets","classes_config.json")
    if os.path.exists(config_filepath):
        with open(config_filepath, "r", encoding="utf-8") as f:
            stored_dirs = json.load(f)
        if stored_dirs:
            # تشغيل الدالة والحصول على التقرير مباشرة
            analyze_and_count_img_extension(stored_dirs)
        else:
            print("The configuration file is empty!")
    else:
        print(f"Error: Config file not found at: {config_filepath}")