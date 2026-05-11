"""
Render the deployment view using PlantUML.

Writes a .puml file (text UML source) and renders it to PNG.

The service set and classification is a small allowlist below: docker-compose.yml
also contains autoheal and zapi_dev variants which we deliberately omit from
the architectural view.

Usage:
    python render_deployment.py
"""

import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "report" / "figures"

PUML = """\
@startuml
skinparam componentStyle uml2
skinparam shadowing false
skinparam defaultFontName Helvetica
skinparam defaultFontSize 14
skinparam ArrowColor #94a3b8
skinparam ArrowFontColor #64748b
skinparam ArrowFontSize 12

skinparam node {
    BackgroundColor #f1f5f9
    BorderColor #94a3b8
    FontColor #64748b
}

skinparam component {
    BackgroundColor<<app>>      #dc2626
    FontColor<<app>>            white
    BorderColor<<app>>          #b91c1c
    BackgroundColor<<service>>  #2563eb
    FontColor<<service>>        white
    BorderColor<<service>>      #1d4ed8
    BackgroundColor<<external>> #f1f5f9
    FontColor<<external>>       #1e293b
    BorderColor<<external>>     #94a3b8
}

skinparam database {
    BackgroundColor<<store>>    #1e293b
    FontColor<<store>>          white
    BorderColor<<store>>        #0f172a
}

node "Docker Host" as host {
  component "Zeeguu API\\nFlask / Apache, port 8080"           as api    <<app>>

  together {
    database  "MySQL 5.7\\nmain database"                      as mysql  <<store>>
    database  "MySQL 5.7\\nmonitoring (FMD)"                   as fmd    <<store>>
    database  "Elasticsearch\\narticle search, 512 MB limit"   as es     <<store>>
  }
  together {
    component "Readability\\ncontent extraction"               as read   <<service>>
    component "Embedding API\\nsemantic vectors, 2.5 GB limit" as emb    <<service>>
    component "Stanza NLP\\n15 lang models, 10 GB limit"       as stanza <<service>>
  }
}

component "Zeeguu React\\nstatic frontend (separate deploy)" as react <<external>>

react  --> api    : REST API
api    --> mysql  : SQL
api    --> fmd    : SQL
api    --> es     : REST
api    --> read   : HTTP
api    --> emb    : HTTP
api    --> stanza : HTTP

' Hidden edges force the data stores and services into two stacked rows
mysql -[hidden]down- read
fmd   -[hidden]down- emb
es    -[hidden]down- stanza

footer Extracted from docker-compose.yml | All containers on a single Docker host | Shared zeeguu_backend network
@enduml
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    puml_path = OUTPUT_DIR / "deployment_view.puml"
    puml_path.write_text(PUML)

    subprocess.run(["plantuml", "-tsvg", str(puml_path)], check=True)
    svg_path = puml_path.with_suffix(".svg")
    pdf_path = puml_path.with_suffix(".pdf")
    subprocess.run(
        ["rsvg-convert", "-f", "pdf", "-o", str(pdf_path), str(svg_path)],
        check=True,
    )
    print(f"  Saved: {pdf_path}")


if __name__ == "__main__":
    main()
