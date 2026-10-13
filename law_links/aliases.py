"""Names of laws that law_aliases.json lacks, made from the names it has.

Court texts write "КАС РФ", "КРФоАП", "Кодекса РФ об АП"; the dictionary
has only the full names of these codes. A code is found by its full name,
so the extension works for any version of the dictionary; an abbreviation
two codes could share (ВК: Водный and Воздушный) is not added.

"Федерального закона от 25.04.2002 № 40-ФЗ" without a title: the dictionary
has the number with the date only together with the title, and the number
alone is shared by two laws; the number with the date is added.
"""

import re
from typing import Dict, List

_SHORT_NAMES = {
    "кодекс административного судопроизводства": ["КАС"],
    "кодекс об административных правонарушениях": ["КоАП", "КРФоАП", "КРФобАП", "Кодекс РФ об АП", "Кодекс об АП"],
    "градостроительный кодекс": ["ГрК"],
    "кодекс внутреннего водного транспорта": ["КВВТ"],
    "кодекс торгового мореплавания": ["КТМ"],
}
_COUNTRY = ["", " РФ", " России", " Российской Федерации"]
_NUMBER_DATE_RE = re.compile(r"^(.+?№\s*[^\s«\"]+\s+от\s+\d{2}\.\d{2}\.\d{4})\s*[«\"]")


def extend(aliases: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """A copy of `aliases` with number-and-date names and short names of codes."""
    result = {law_id: list(names) for law_id, names in aliases.items()}
    for names in result.values():
        known = {n.lower() for n in names}
        for name in list(names):
            m = _NUMBER_DATE_RE.match(name)
            if m and m.group(1).lower() not in known:
                known.add(m.group(1).lower())
                names.append(m.group(1))
    for full, shorts in _SHORT_NAMES.items():
        for law_id, names in result.items():
            if any(n.lower().replace(" российской федерации", "").replace(" рф", "").strip() == full for n in names):
                known = {n.lower() for n in names}
                result[law_id] += [
                    s + c for s in shorts for c in ([""] if " " in s else _COUNTRY) if (s + c).lower() not in known
                ]
                break
    return result
