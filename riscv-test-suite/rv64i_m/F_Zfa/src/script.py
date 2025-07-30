import os

# --- CONFIGURATION ---
extension = "F_Zfa"         # Change this as needed
target_folder = "./"      # Set to the folder containing the .S files

# --- Self-check block template (based on filename) ---
def make_selfchk_block(filename_no_ext):
    return (
        '#ifdef RVTEST_SELFCHK_MODE\n'
        f'    #include "../../../Reference/rv64i_m/{extension}/src/{filename_no_ext}.S"\n'
        '#else'
    )

def process_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    filename_no_ext = os.path.splitext(os.path.basename(filepath))[0]
    selfchk_block = make_selfchk_block(filename_no_ext)

    new_lines = []
    inserted_selfchk = False
    inserted_endif = False

    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Insert self-check block AFTER CANARY;
        if not inserted_selfchk and "RVMODEL_DATA_BEGIN" in line:
            while i + 1 < len(lines):
                i += 1
                new_lines.append(lines[i])
                if "CANARY;" in lines[i-1]:
                    new_lines.append(selfchk_block)
                    inserted_selfchk = True
                    break

        # Insert #endif BEFORE gpr save line, with a blank line
        elif not inserted_endif and "#ifdef rvtest_gpr_save" in line:
            new_lines.insert(len(new_lines) - 1, "#endif\n\n")
            inserted_endif = True

        i += 1

    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    print(f"✅ Modified: {filepath}")

def process_all_S_files(folder):
    for filename in os.listdir(folder):
        if filename.endswith(".S"):
            filepath = os.path.join(folder, filename)
            process_file(filepath)

if __name__ == "__main__":
    process_all_S_files(target_folder)
