import re, pathlib
text = pathlib.Path("artifacts/js-coverage/lcov.info").read_text()
for rec in text.split("end_of_record"):
    m = re.search(r"SF:(.*)", rec)
    if not m:
        continue
    zeros = [int(x) for x in re.findall(r"DA:(\d+),0", rec)]
    if zeros:
        print(m.group(1))
        print(zeros)
