#!/usr/bin/env python3
"""
Teste local para validar o ciclo completo do proxy usando um ooproxy de teste.

1. Cria um ooproxy.py temporário que lê OOPROXY_API_KEY do env.
2. Configura OOPROXY_HOME para o diretório temporário.
3. Inicia o proxy via ProxyController.
4. Verifica que o processo começa e lê a chave gravada pelo script.
5. Para o proxy e garante que o status finaliza em STOPPED.
"""

import sys
import time
import textwrap
import tempfile
from pathlib import Path

# Adicionar o root ao path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication
from controllers.proxy_controller import ProxyController
from gui.models.proxy_state import ProxyStatus
from gui.resources import set_ooproxy_home, get_ooproxy_script, get_python_path


def create_dummy_ooproxy(tmp_root: Path) -> None:
    script_path = tmp_root / "ooproxy.py"
    script_path.write_text(
        (
            "import os\n"
            "import sys\n"
            "import time\n"
            "\n"
            "def main():\n"
            "    api_key = os.environ.get(\"OOPROXY_API_KEY\", \"\")\n"
            "    output_file = os.path.join(os.path.dirname(__file__), \"api_key.txt\")\n"
            "    with open(output_file, \"w\", encoding=\"utf-8\") as f:\n"
            "        f.write(api_key)\n"
            "    sys.stdout.write(f\"STARTED api_key_exists={bool(api_key)}\\n\")\n"
            "    sys.stdout.flush()\n"
            "    try:\n"
            "        while True:\n"
            "            time.sleep(0.1)\n"
            "    except KeyboardInterrupt:\n"
            "        pass\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    main()\n"
        ),
        encoding="utf-8",
    )


def test_proxy_lifecycle() -> bool:
    print("=" * 72)
    print("TESTE LOCAL REAL DO PROXY - validação de OOPROXY_API_KEY via env")
    print("=" * 72)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        create_dummy_ooproxy(tmp_root)
        set_ooproxy_home(tmp_root)

        print(f"Diretório de ooproxy temporário: {tmp_root}")
        print(f"Script ooproxy: {get_ooproxy_script()}")
        print(f"Python usado: {get_python_path()}")

        app = QApplication.instance() or QApplication(sys.argv)
        controller = ProxyController()
        key = "secret-test-key"
        url = "http://localhost"
        port = 11434
        status_changes: list[str] = []
        log_lines: list[str] = []

        def on_status(status):
            status_changes.append(str(status))
            print(f"[STATUS] {status}")

        def on_log(line: str):
            log_lines.append(line)
            print(f"[LOG] {line}")

        controller.status_changed.connect(on_status)
        controller.log_received.connect(on_log)

        print("\n1. Iniciando proxy de teste...")
        controller.start_proxy(url, key, port)

        start_time = time.time()
        while time.time() - start_time < 5:
            app.processEvents()
            if controller._process and controller._process.is_running():
                break
            time.sleep(0.1)

        if not controller._process or not controller._process.is_running():
            print("✗ O processo do proxy não iniciou corretamente.")
            return False

        print(f"Status após iniciar: {controller.get_status()}")

        time.sleep(0.5)
        api_key_file = tmp_root / "api_key.txt"
        if not api_key_file.exists():
            print("✗ O script de proxy de teste não gravou api_key.txt.")
            return False

        api_key_value = api_key_file.read_text(encoding="utf-8")
        print(f"Arquivo api_key.txt: {api_key_value!r}")
        if api_key_value != key:
            print("✗ A chave recebida pelo processo não coincide com a chave esperada.")
            return False

        print("\n2. Parando proxy...")
        controller.stop_proxy()
        stop_deadline = time.time() + 5
        while time.time() < stop_deadline:
            app.processEvents()
            current_status = controller.get_status()
            if current_status in (ProxyStatus.STOPPED, ProxyStatus.ERROR):
                break
            time.sleep(0.1)

        final_status = controller.get_status()
        print(f"Status final: {final_status}")
        if final_status != ProxyStatus.STOPPED:
            print("✗ O proxy não finalizou corretamente.")
            return False

        print("\n✓ Teste local do proxy finalizado com sucesso.")
        return True


if __name__ == "__main__":
    success = test_proxy_lifecycle()
    sys.exit(0 if success else 1)
