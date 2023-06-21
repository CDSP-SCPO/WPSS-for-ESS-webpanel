# WPSS user documentation

- GitHub repo: <https://github.com/CDSP-SCPO/wpss-doc/>
- GitHub pages: <https://cdsp-scpo.github.io/wpss-doc/>

## Add github remote

`git remote add github git@github.com:CDSP-SCPO/wpss-doc.git`

## Publish new version

merge master into production or documentation branches

## Preview

- `mkdocs serve -a 0.0.0.0:8888`

## Rules

* Naming convention: all in lowercase, `-` to split words


File tree structure
- docs: files automatically put online, so displayed
- hidden-docs: other files to be used as working documents. hq and pnlt

Each of these folders contains sub-folders distinguishing the different users and an image file (img). The latter contains sub-folders specifying the user to whom it is attached (e.g. img-nc).
