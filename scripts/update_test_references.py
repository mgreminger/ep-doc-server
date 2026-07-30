# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///

import os
import subprocess
import shutil
import sys

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
    print("(Note: Tests are EXPECTED to fail because references are outdated.)")
    
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

    # 5. Overwrite the reference files
    print("Updating reference files...")
    updated_count = 0
    for filename in os.listdir(extracted_output_dir):
        ref_name = get_reference_name(filename)
        if ref_name:
            src = os.path.join(extracted_output_dir, filename)
            dst = os.path.join(host_tests_dir, ref_name)
            shutil.copy2(src, dst)
            print(f"  ✓ {filename} -> {ref_name}")
            updated_count += 1

    # 6. Verify the update by running tests again
    print("\nVerifying the update by running tests again with new references...")
    
    # Create the verification container
    subprocess.run(["docker", "create", "--name", verifier_container, image_name, "pytest"])
    
    # Copy the newly updated tests directory from the host into the verification container
    subprocess.run(["docker", "cp", f"{host_tests_dir}/.", f"{verifier_container}:/code/tests/"])
    
    # Run the tests
    verify_result = subprocess.run(["docker", "start", "-a", verifier_container])
    tests_passed = verify_result.returncode == 0

    # 7. Cleanup
    print("\nCleaning up...")
    subprocess.run(["docker", "rm", "-f", container_name, verifier_container], capture_output=True)
    shutil.rmtree(extracted_output_dir)

    if tests_passed:
        print(f"\nSuccess! Updated {updated_count} reference files and verified tests pass.")
    else:
        print(f"\nWarning: Updated {updated_count} reference files, but the verification tests failed! Please review the test output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
