# fyz-lab-stamp

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-10%2B-informational)
![GUI](https://img.shields.io/badge/GUI-tkinter-success)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![CTU](https://img.shields.io/badge/%C4%8CVUT-Katedra%20fyziky-0065BD)
![Language](https://img.shields.io/badge/lang-%C4%8De%C5%A1tina-red)
![Last commit](https://img.shields.io/github/last-commit/Janxyxy/fyz-lab-stamp)

Vyplní razítko protokolu z laboratorního cvičení z fyziky (ČVUT) textem ze souboru JSON nebo z grafického formuláře.

📄 **[Jak vypracovat laboratorní úlohu z fyziky](docs/jak-vypracovat-ulohu.docx)**: stručný návod, který shrnuje laboratorní řád, co má obsahovat protokol, nejistoty měření, tabulky a grafy, zápis výsledku a odevzdání a body.

## Instalace a použití

```
pip install -r requirements.txt
cp data.example.json data.json      # pak vyplň své údaje
python fill_stamp.py                # razitko.jpg + data.json -> razitko_filled.png
```

Nebo použij grafické rozhraní (formulář s živým náhledem, výběr úlohy ze seznamu, uložení PNG / data.json):

```
python gui.py
```

Hodnoty lze přepsat i bez úpravy JSONu:

```
python fill_stamp.py --set task_number=3 --set "task_name=Měření tíhového zrychlení"
```

## Klíče v JSONu

Prázdné nebo chybějící klíče zůstanou na razítku nevyplněné.

| Klíč | Pole na razítku |
|---|---|
| `name` | Jméno |
| `measurement_date` | Datum měření |
| `study_year` | Stud. rok |
| `year` | Ročník |
| `submission_date` | Datum odevzdání |
| `study_group` | Stud. skupina |
| `lab_group` | Lab. skupina |
| `classification` | Klasifikace |
| `task_number` | Číslo úlohy |
| `task_name` | Název úlohy |

Navíc klíč `semester` (`1`, `2`, `3`): spolu s `task_number` podle něj skript najde název úlohy v `tasks.json` (seznamy úloh pro jednotlivé semestry; když se změní, stačí soubor upravit).

Automaticky se doplní, pokud jsou prázdné:
- `task_name` → z `tasks.json` podle `semester` + `task_number`
- `submission_date` → dnešní datum
- `study_year` → akademický rok podle `measurement_date` (např. `2026/2027`)

Dlouhé názvy úloh se zmenší, a když je potřeba, zalomí se na dva řádky.

## Volitelné přepínače

- `-o out.png`: jiný výstupní soubor
- `--font cesta/k/fontu.ttf`: jiný font (musí podporovat češtinu)
- `--color 0a0a78`: barva textu
- `--scale 4`: rozlišení výstupu

`data.json` je v `.gitignore`, takže tvoje osobní údaje zůstanou jen u tebe.
