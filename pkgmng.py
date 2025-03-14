import os
import shutil
import zipfile
import hcl2
import hashlib
import requests
import datetime
import subprocess


# --- Функция вычисления SHA256 ---
def compute_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()


# --- Функция распаковки ZIP-архива ---
def extract_package(zip_path, extract_to="./extracted"):
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)
    os.makedirs(extract_to)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    print(f"✅ Архив {zip_path} распакован в {extract_to}")
    return extract_to


# --- Функция загрузки HCL-манифеста ---
def load_manifest(manifest_path):
    with open(manifest_path, "r") as f:
        return hcl2.load(f)


# --- Функция скачивания файла ---
def download_file(url, dest_path, expected_sha256=None):
    print(f"🔽 Скачивание: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    if expected_sha256:
        computed_sha = compute_sha256(dest_path)
        if computed_sha != expected_sha256:
            os.remove(dest_path)
            raise ValueError(f"❌ SHA256 не совпадает! Ожидалось: {expected_sha256}, получено: {computed_sha}")

    print(f"✅ Файл загружен: {dest_path}")


# --- Функция проверки наличия Go ---
def check_go_installed():
    try:
        result = subprocess.run(["go", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Найден компилятор Go: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        return False
    return False


# --- Функция установки Go ---
def install_go(go_info):
    go_url = go_info["source"]
    go_sha256 = go_info["sha256"]
    go_archive = "/tmp/go.tar.gz"

    download_file(go_url, go_archive, go_sha256)

    if os.path.exists("/usr/local/go"):
        shutil.rmtree("/usr/local/go")

    os.system(f"tar -C /usr/local -xzf {go_archive}")
    os.environ["PATH"] += os.pathsep + "/usr/local/go/bin"
    print("✅ Компилятор Go установлен!")


# --- Функция сборки Go-приложения ---
def build_go_project(project_path, entry_point, output_binary):
    os.chdir(project_path)
    os.makedirs("bin", exist_ok=True)

    binary_path = f"bin/{output_binary}"
    build_cmd = f"go build -o {binary_path} {entry_point}"
    result = subprocess.run(build_cmd, shell=True)

    if result.returncode != 0:
        raise RuntimeError("❌ Ошибка сборки!")

    print(f"✅ Сборка завершена. Бинарник: {binary_path}")
    return os.path.join(project_path, binary_path)


# --- Функция создания манифеста HCL ---
def create_manifest(binary_path, entry_point, dependencies):
    manifest_content = f"""
    name = "my-go-app"
    version = "1.0.0"
    entry_point = "{entry_point}"
    date = "{datetime.datetime.now().isoformat()}"

    output_binary = "{os.path.basename(binary_path)}"
    sha256 = "{compute_sha256(binary_path)}"

    supported_os = ["linux"]
    supported_architectures = ["amd64"]

    dependencies = [
        {{"name" = "{dependencies[0]['name']}", "version" = "{dependencies[0]['version']}", "source" = "{dependencies[0]['source']}", "sha256" = "{dependencies[0]['sha256']}"}}
    ]
    """

    with open("manifest.hcl", "w") as f:
        f.write(manifest_content.strip())

    print("✅ Файл manifest.hcl создан!")


# --- Функция запуска собранного приложения ---
def run_binary(binary_path):
    print(f"🚀 Запуск: {binary_path}")
    subprocess.run([binary_path])


# --- Основная логика работы менеджера ---
def main(zip_path):
    extracted_path = extract_package(zip_path)
    manifest_path = os.path.join(extracted_path, "manifest.hcl")

    if not os.path.exists(manifest_path):
        raise FileNotFoundError("❌ Файл manifest.hcl не найден!")


    manifest = load_manifest(manifest_path)
    print(f"📜 Манифест загружен: {manifest}")

    # Проверяем и устанавливаем Go
    if not check_go_installed():
        install_go(manifest["dependencies"][0])  # В данном примере зависимость только одна

    # Собираем приложение
    binary_path = build_go_project(extracted_path, manifest["entry_point"], manifest["output_binary"])

    # Проверяем SHA256
    computed_sha256 = compute_sha256(binary_path)
    if computed_sha256 != manifest["sha256"]:
        print("❌ Контрольная сумма не совпадает! Возможно, что-то пошло не так.")
    else:
        print("✅ Контрольная сумма совпадает.")

    # Обновляем манифест с актуальной SHA256
    create_manifest(binary_path, manifest["entry_point"], manifest["dependencies"])

    # Запускаем собранное приложение
    run_binary(binary_path)

# --- Точка входа ---
if __name__ == "__main__":
    zip_file = "test-package.zip"  # Укажи свой ZIP-архив
    main(zip_file)