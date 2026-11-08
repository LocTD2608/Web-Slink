"""Read Docker's measured stats on the host, expose Prometheus textfile metrics."""
import json, re, subprocess, time, pathlib, argparse

def bytes_value(value):
    match = re.fullmatch(r"\s*([0-9.]+)\s*([A-Za-z]*)\s*", value)
    if not match:
        raise ValueError(value)
    number, unit = match.groups()
    factors = {"B":1,"kB":1000,"KB":1000,"MB":1000**2,"GB":1000**3,"KiB":1024,"MiB":1024**2,"GiB":1024**3}
    return float(number)*factors[unit or "B"]

def sample(output):
    raw = subprocess.check_output(["docker","stats","--no-stream","--format","{{json .}}"], text=True, encoding="utf-8")
    lines = []
    for line in raw.splitlines():
        row = json.loads(line)
        if not row["Name"].startswith("course-lab-") or row["Name"].startswith("course-lab-test-"):
            continue
        labels = '{container="'+row["Name"]+'"}'
        rx, tx = row["NetIO"].split("/")
        fields = {"cpu_cores":float(row["CPUPerc"].rstrip("%"))/100,
                  "memory_bytes":bytes_value(row["MemUsage"].split("/")[0]),
                  "network_receive_bytes_total":bytes_value(rx), "network_transmit_bytes_total":bytes_value(tx)}
        for name, value in fields.items():
            lines.append(f"lab_container_{name}{labels} {value}")
    lines.append(f"lab_container_sample_timestamp_seconds {time.time()}")
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    tmp.write_text("\n".join(lines)+"\n", encoding="utf-8")
    tmp.replace(output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    dest = pathlib.Path(__file__).resolve().parents[1]/"artifacts/metrics/containers.prom"
    while True:
        try:
            sample(dest)
        except Exception as exc:
            print(type(exc).__name__, str(exc), flush=True)
            if args.once: raise
        if args.once: break
        time.sleep(3)
