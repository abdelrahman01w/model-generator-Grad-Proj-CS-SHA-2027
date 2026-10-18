import os
import json
import cv2 as cv
from collections import defaultdict
from PIL import Image
import numpy as np

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


def analyze_and_validate_classes():

    # get config_file and project route
    current_script_path = os.path.dirname(os.path.abspath(__file__))

    project_route = current_script_path

    for _ in range(4):
        project_route=os.path.dirname(project_route)

    config_filepath = os.path.join(project_route , "assets" , "classes_config.json")

    if not os.path.exists(config_filepath):
        print(f"Error: Config file not found at: {config_filepath}")
        print("Please run your setup script first to generate the directories configuration!")
        return None
    
    with open(config_filepath , "r" , encoding="utf-8") as f:
        stored_dirs=json.load(f)

    if not stored_dirs:
        print("The configuration file is empty!")
        return None
    print(f"Found {len(stored_dirs)} classes in the configuration file. Starting validation based on content...\n")

    # allowed extension
    allowed_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    validated_dirs = {}

    # some info about files
    global_accepted_count = 0
    global_rejected_count = 0

    # catch each class
    for class_name,class_path in stored_dirs.items():
        print(f"=" * 50)
        print(f"Processing -> [{class_name}] at: {class_path}")
        print(f"=" * 50)

        if not os.path.isdir(class_path):
            print(f"REJECTED CLASS: [{class_name}] - Reason: The directory path does not exist.\n")
            continue
        all_files = os.listdir(class_path)
        
        # image_candidates --> store img's_name which exist in path
        image_candidates = [
            f for f in all_files if os.path.isfile(os.path.join(class_path, f))
            ]
        
        if not image_candidates:
            print(f"REJECTED CLASS: [{class_name}] - Reason: The directory is completely empty.\n")
            continue
        class_accepted_images = []
        class_rejected_files = {} # store file name with reason

        for filename in image_candidates:
            img_path  = os.path.join(class_path,filename)
            ext = os.path.splitext(filename)[1].lower()

            # Rule 1 : check from  extension with reject and reason for rejection
            if ext not in allowed_extensions:
                class_rejected_files[filename] =f"Invalid extension '{ext}' (Not allowed)"
                continue

            # Rule 2 : check from content (Content-based verification) using opencv
            try:
                img=cv.imread(img_path)
                if img is None:
                    class_rejected_files[filename] = "Corrupted file or content is not a valid image format"
                else:
                    class_accepted_images.append(filename)
                    print(f" Accepted: {filename} [{ext.upper()}]")
            except Exception as e:
                class_rejected_files[filename] = f"Error reading file content: {str(e)}"
        
        print("-" * 50)

        if len(class_accepted_images) == 0:
            print(f"REJECTED CLASS: [{class_name}]")
            print(f"Reason: All files in this class were rejected!")
        else:
            print(f" Class [{class_name}] Status: PASSED")
            print(f" - Accepted Images: {len(class_accepted_images)}")
            global_accepted_count += len(class_accepted_images)
            validated_dirs[class_name] = class_path

        # report for rejected files
        if class_rejected_files:
            print(f"\n  Rejected Files Report for [{class_name}]:")
            for rej_file, reason in class_rejected_files.items():
                print(f"    - '{rej_file}' -> Reason: {reason}")
                global_rejected_count += 1
        else:
            print(f"  - No rejected files in this class.")

        print("\n")


    # A Genral report
    print("========================================")
    print("       FINAL CONTENT VALIDATION REPORT  ")
    print("========================================")
    print(f"Total Accepted Images : {global_accepted_count}")
    print(f"Total Rejected Files  : {global_rejected_count}")
    print("========================================")
    return validated_dirs

# verify_images_deep_integrity

def verify_images_deep_integrity(validated_dirs) :
    """
    Examine the accepted images to ensure they can be fully opened and decoded 
    (detecting truncated or internally corrupted images).
    """
    print("========================================")
    print("       DEEP INTEGRITY  ")
    print(" (Checking for Truncated/Corrupted) ")
    print("========================================")

    if not validated_dirs:
        print("No classes passed Layer 1 to perform deep integrity check.")
        return {}

    fully_validated_classes = defaultdict(list)
    fully_valid_count = 0
    corrupted_or_truncated_count = 0

    for class_name,class_path in validated_dirs.items():
        print(f"\n Deep Checking [{class_name}]...")

        images_files = [
            f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path,f))
        ]

        for file_name in images_files:
            img_path = os.path.join(class_path, file_name)
            # Using Pillow to open and fully decode an image (calling `load()` forces the actual decoding of the data)
            try:
                with Image.open(img_path) as img :
                    img.load() # Forcing Pillow to read image data and decode it into pixel data
                fully_validated_classes[class_name].append(img_path)
                print(f"  Fully Decoded & Valid: {file_name}")
                fully_valid_count += 1  
            except(IOError , SyntaxError,OSError): 
                # IOError --> error in read img daya
                # SyntaxError -->problem in archticture of img
                # OSError --> error in file or less data
                corrupted_or_truncated_count += 1
                print(f"  TRUNCATED/CORRUPTED REJECTED: {file_name} -> Reason: {str(e)}")
            except Exception as e :
                corrupted_or_truncated_count += 1
                print(f"  ERROR DECODING: {file_name} -> Reason: {str(e)}")
    print("\n========================================")
    print("       FINAL DEEP INTEGRITY REPORT      ")
    print("========================================")
    print(f"Fully Valid & Intact Images : {fully_valid_count}")
    print(f"Truncated / Corrupted Files : {corrupted_or_truncated_count}")
    print("========================================")

    return fully_validated_classes

def verfiy_images_size(deep_checked_classes):
    print("\n========================================")
    print("      CHECK IMAGE SIZE VALIDATION    ")
    print("      (Checking 0 bytes & > 20MB)       ")
    print("========================================")

    if not deep_checked_classes:
        print("No classes provided for size validation.")
        return{}

    final_clean_class = defaultdict(list)
    accepted_size_count = 0
    rejected_size_count = 0

    MAX_SIZE_BYTES = 20 * 1024*1024

    for class_name, img_paths in deep_checked_classes.items():
        print(f"\n Checking sizes for [{class_name}]...")

        for img_path in img_paths:
            file_name = os.path.basename(img_path)

            try: 
                file_size_bytes=os.path.getsize(img_path) # get size by kb
                file_size_mb = file_size_bytes/ (1024*1024) # convert size by mb

                # first condition "reject file if it = 0 mb"
                if file_size_bytes ==0:
                    rejected_size_count += 1
                    print(f" REJECTED: {file_name} -> Reason: File size is 0 bytes (Empty file)")
                    continue

                # first condition "reject file if it greater than > 20 mb"

                if file_size_bytes > MAX_SIZE_BYTES:
                    rejected_size_count += 1
                    print(f" REJECTED: {file_name} -> Reason: File size is too large ({file_size_mb:.2f} MB > 20 MB)")
                    continue
                final_clean_class[class_name].append(img_path)
                accepted_size_count += 1
                print(f"  Size Accepted: {file_name} [{file_size_mb:.2f} MB]")
            except Exception as e:
                rejected_size_count += 1
                print(f"  ERROR checking size for {file_name} -> Reason: {str(e)}")
    print("\n========================================")
    print("        FINAL SIZE VALIDATION REPORT    ")
    print("========================================")
    print(f"Images Passed Size Check : {accepted_size_count}")
    print(f"Images Rejected by Size  : {rejected_size_count}")
    print("========================================")
    return final_clean_class

# 	Shorter side below 64 px ==> Reject

def verify_images_resolution(size_passed_classes):
    print("\n==================================================")
    print("         CHAECK RESOLUTION     ")
    print("      (Shorter side must be >= 64 pixels)         ")
    print("==================================================")

    if not size_passed_classes:
        print("No classes provided for resolution validation.")
        return {}
    
    final_clean_dict = defaultdict(list)
    accepted_res_count = 0
    rejected_res_count = 0

    for class_name, img_paths in size_passed_classes.items():
        print(f"\n Checking resolutions for [{class_name}]...")
        for img_path in img_paths:
            file_name = os.path.basename(img_path)
            try:
                with Image.open(img_path) as img:
                    width, height = img.size
                    shorter_side = min(width, height)

                    # if shorter_side img less than 64 px --> rejected
                    if shorter_side < 64:
                        rejected_res_count += 1
                        print(f"   REJECTED: {file_name} -> Resolution {width}x{height} (Shorter side {shorter_side}px < 64px)")
                        continue
                    # success
                    final_clean_dict[class_name].append(img_path)
                    accepted_res_count += 1
                    print(f"   Accepted: {file_name} [{width}x{height}px]")
            except Exception as e:
                rejected_res_count += 1
                print(f"  ERROR checking resolution for {file_name} -> Reason: {str(e)}")
    print("\n========================================")
    print("      FINAL RESOLUTION REPORT           ")
    print("========================================")
    print(f"Images Accepted in Dictionary : {accepted_res_count}")
    print(f"Images Rejected (< 64px)      : {rejected_res_count}")
    print("========================================")
    return final_clean_dict

# Verifiy aspect ratio 

def verify_images_aspect_ratio(resolution_passed_classes):
    print("\n==================================================")
    print("      Check ASPECT RATIO VALIDATION            ")
    print("      (Aspect ratio must not exceed 3:1)          ")
    print("==================================================")

    if not resolution_passed_classes:
        print("No classes provided for aspect ratio validation.")
        return {}

    final_clean_dict = defaultdict(list)
    accepted_ar_count = 0
    rejected_ar_count = 0

    for class_name, img_paths in resolution_passed_classes.items():
        print(f"\n Checking aspect ratios for [{class_name}]...")
        for img_path in img_paths:
            file_name = os.path.basename(img_path)
            
            try:
                with Image.open(img_path) as img:
                    width, height = img.size
                    max_dim = max(width, height)
                    min_dim = min(width, height)
                    # Calculating the aspect ratio (the longer side to the shorter side)
                    aspect_ratio = max_dim / min_dim

                    # if aspect ratio above 3:1 --> reject
                    if aspect_ratio > 3.0:
                        rejected_ar_count += 1
                        print(f"  REJECTED: {file_name} -> Aspect ratio {max_dim}:{min_dim} ({aspect_ratio:.2f}:1 > 3:1)")
                        continue
                    # accepted
                    final_clean_dict[class_name].append(img_path)
                    accepted_ar_count += 1
                    print(f"  Aspect Ratio Accepted: {file_name} [{width}x{height}, Ratio: {aspect_ratio:.2f}:1]")
            except Exception as e:
                rejected_ar_count += 1
                print(f"  ERROR checking aspect ratio for {file_name} -> Reason: {str(e)}")
    print("\n========================================")
    print("      FINAL ASPECT RATIO REPORT         ")
    print("========================================")
    print(f"Final Clean Images Accepted : {accepted_ar_count}")
    print(f"Images Rejected (> 3:1 AR)  : {rejected_ar_count}")
    print("========================================")

    return final_clean_dict

# 6. check 	Blank image: pixel variation almost zero (all black, all white, one flat color)

def verify_images_pixel_variation(aspect_ratio_passed_classes):
    print("\n==================================================")
    print("      CHECK PIXEL VARIATION / BLANK CHECK      ")
    print("      (Rejecting flat color, all black, white)    ")
    print("==================================================")

    if not aspect_ratio_passed_classes:
        print("No classes provided for pixel variation validation.")
        return {}

    final_clean_dict = defaultdict(list)
    accepted_pixel_count = 0
    rejected_pixel_count = 0

    # (Standard Deviation Threshold)
    # If it is less than 1.0, it means the image is nearly identical in terms of its pixels (consisting of a single color or being almost empty).

    STD_THRESHOLD = 1.0

    for class_name, img_paths in aspect_ratio_passed_classes.items():
        print(f"\n Checking pixel variations for [{class_name}]...")

        for img_path in img_paths:
            file_name = os.path.basename(img_path)

            try: 
                # Reading an image in grayscale using OpenCV to examine pixel contrast
                gray_img = cv.imread(img_path, cv.IMREAD_GRAYSCALE)

                if gray_img is None:
                    rejected_pixel_count += 1
                    print(f"  REJECTED: {file_name} -> Reason: Could not load for pixel check")
                    continue
                # Calculating the Standard Deviation of Pixels
                pixel_std = np.std(gray_img)

                # If the contrast is non-existent or nearly non-existent (a black or white image, or a solid, flat color)
                if pixel_std < STD_THRESHOLD:
                    rejected_pixel_count += 1
                    print(f"  REJECTED: {file_name} -> Reason: Blank or flat color image (Pixel Std Dev: {pixel_std:.2f} < {STD_THRESHOLD})")
                    continue

                # success
                final_clean_dict[class_name].append(img_path)
                accepted_pixel_count += 1
                print(f"  Clean & Accepted: {file_name} [Std Dev: {pixel_std:.2f}]")

            except Exception as e:
                rejected_pixel_count += 1
                print(f"  ERROR checking pixel variation for {file_name} -> Reason: {str(e)}")
    print("\n========================================")
    print("     FINAL PIXEL VARIATION REPORT       ")
    print("========================================")
    print(f"Final Clean Images Accepted : {accepted_pixel_count}")
    print(f"Images Rejected (Blank/Flat): {rejected_pixel_count}")
    print("========================================")
    return final_clean_dict


if __name__ == "__main__":
    passed_classes_check_1 = analyze_and_validate_classes()
    if passed_classes_check_1:
        passed_img_opened_check2 = verify_images_deep_integrity(passed_classes_check_1)
        
        if passed_img_opened_check2:
            passed_img_size_cechk3 = verfiy_images_size(passed_img_opened_check2)
            
            if passed_img_size_cechk3:
                
                passed_img_shorter_side_cechk4 = verify_images_resolution(passed_img_size_cechk3)
        
                if passed_img_shorter_side_cechk4:

                    passed_aspect_ratio_ceck5 = verify_images_aspect_ratio(passed_img_shorter_side_cechk4)
                    
                    if passed_aspect_ratio_ceck5:
                        
                        final_dataset_dict = verify_images_pixel_variation(passed_aspect_ratio_ceck5)
        print("\n Full Pipeline Completed Successfully!")
        print(" Final dataset dictionary is ready in memory:")
        for c_name, paths in passed_img_size_cechk3.items():
            print(f"Class '{c_name}' has {len(paths)} ready-to-use images.")
