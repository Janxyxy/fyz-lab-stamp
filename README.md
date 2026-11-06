# fyz-lab-stamp

Fills the stamp (razítko) of the CTU physics lab protocol with text from a JSON file.

```
pip install pillow
python fill_stamp.py razitko.jpg data.json            # -> razitko_filled.png
python fill_stamp.py razitko.jpg data.json -o out.png
```

JSON keys (empty or missing ones stay blank): `name`, `measurement_date`, `study_year`, `year`, `submission_date`, `study_group`, `lab_group`, `classification`, `task_number`, `task_name`.

Optional flags: `--font path/to/font.ttf` (must support Czech), `--color 0a0a78`.
