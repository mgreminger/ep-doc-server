# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///

import os
import subprocess
import shutil
import sys
import argparse
import filecmp

def get_reference_name(output_filename):
    """Maps an output filename to its corresponding reference filename."""
    name, ext = os.path.splitext(output_filename)
    
    if name == "output":
        return f"output_reference{ext}"
    elif name.startswith("output_"):
        # e.g., output_a4.docx -> output_reference_a4.docx
        suffix = name[len("output_"):]
        return f"output_reference_{suffix}{ext}"
    return None

def main():
    parser = argparse.ArgumentParser(description="Update test references for the document server.")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="List the files that would be changed without actually replacing them."
    )
    args = parser.parse_args()
    is_dry_run = args.dry_run

    container_name = "ep-test-runner"
    verifier_container = "ep-test-verifier"
    image_name = "ep-doc-server-tests"
    host_tests_dir = os.path.abspath("./tests")
    extracted_output_dir = os.path.abspath("./tests/extracted_output")

    # 1. Clean up any previous runs
    subprocess.run(["docker", "rm", "-f", container_name, verifier_container], capture_output=True)
    if os.path.exists(extracted_output_dir):
        shutil.rmtree(extracted_output_dir)

    # 2. Build the Docker image
    print("Building Docker image (this may take a minute)...")
    print("(Note: You can safely ignore the 'legacy builder is deprecated' warning below)")
    
    build_result = subprocess.run([
        "docker", "build", 
        "--build-arg", "ENVIRONMENT=development", 
        "-t", image_name, 
        "."
    ])
    
    if build_result.returncode != 0:
        print("Error: Docker build failed.")
        sys.exit(1)

    # 3. Run the tests inside the container
    print("\nRunning pytest in container...")
    subprocess.run(["docker", "create", "--name", container_name, image_name, "pytest"])
    subprocess.run(["docker", "start", "-a", container_name])

    # 4. Extract the output directory from the container
    print("\nExtracting generated outputs from container...")
    extract_result = subprocess.run([
        "docker", "cp", 
        f"{container_name}:/code/tests/output", 
        extracted_output_dir
    ])
    
    if extract_result.returncode != 0 or not os.path.exists(extracted_output_dir):
        print("Error: Failed to extract output files. Did the tests generate any output?")
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        sys.exit(1)

    # 5. Overwrite (or list) ONLY the files that differ
    if is_dry_run:
        print("\n--- DRY RUN: The following files differ and would be updated ---")
    else:
        print("\nChecking for differences and updating reference files...")
        
    updated_count = 0
    skipped_count = 0
    
    for filename in os.listdir(extracted_output_dir):
        ref_name = get_reference_name(filename)
        if ref_name:
            src = os.path.join(extracted_output_dir, filename)
            dst = os.path.join(host_tests_dir, ref_name)
            
            # If the reference exists and is identical to the output, skip it
            if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
                skipped_count += 1
                continue
                
            # If it doesn't exist or is different, we update it
            if is_dry_run:
                print(f"  Would replace: {ref_name} (using {filename})")
            else:
                shutil.copy2(src, dst)
                print(f"  ✓ Updated: {ref_name}")
                
            updated_count += 1

    print(f"\nChecked files: {updated_count} required updates, {skipped_count} were identical.")

    # 6. Verify the update by running tests again (Skip on dry-run or if no updates needed)
    tests_passed = True
    if not is_dry_run and updated_count > 0:
        print("\nVerifying the update by running tests again with new references...")
        
        subprocess.run(["docker", "create", "--name", verifier_container, image_name, "pytest"])
        subprocess.run(["docker", "cp", f"{host_tests_dir}/.", f"{verifier_container}:/code/tests/"])
        
        verify_result = subprocess.run(["docker", "start", "-a", verifier_container])
        tests_passed = verify_result.returncode == 0
    elif not is_dry_run and updated_count == 0:
        print("\nNo updates were needed. Skipping verification run.")

    # 7. Cleanup
    print("\nCleaning up...")
    subprocess.run(["docker", "rm", "-f", container_name, verifier_container], capture_output=True)
    shutil.rmtree(extracted_output_dir)

    # 8. Final Report
    if is_dry_run:
        print(f"\nDry run complete. {updated_count} reference files would be replaced.")
    elif tests_passed:
        print(f"\nSuccess! Updated {updated_count} reference files.")
    else:
        print(f"\nWarning: Updated {updated_count} reference files, but the verification tests failed! Please review the test output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()