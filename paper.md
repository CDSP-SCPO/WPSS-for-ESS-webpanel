---
title: 'WPSS, a web panel sample service'
tags:
  - Python
  - Django
  - Qualtrics
  - Social Sciences and Humanities
  - FAIR data
  - Quantitative Survey
  - Online panel
authors:
  - name: Quentin Agren
    orcid:
    equal-contrib: true
    affiliation: 1
  - name: Malaury Lemaître-Salmon
    orcid: 0000-0001-6263-9019
    equal-contrib: true
    affiliation: 1
  - name: Genevieve Michaud
    orcid: 0000-0001-9288-2888
    equal-contrib: true
    affiliation: 1
  - name: Baptiste Rouxel
    orcid: 0000-0002-4162-8326
    equal-contrib: true
    affiliation: 1
  - name: Tom Villette
    orcid: 0000-0002-7249-4228
    equal-contrib: true
    affiliation: 1
  - name: Jimmy Barreau
    orcid:
    equal-contrib: false
    affiliation: 1
  - name: Simon Dellac
    orcid:
    equal-contrib: false
    affiliation: 1
  - name: Lothaire Epee
    orcid:
    equal-contrib: false
    affiliation: 1
  - name: El Hassane Gargem
    orcid:
    equal-contrib: false
    affiliation: 1
  - name: Keenen Remir
    orcid:
    equal-contrib: false
    affiliation: 1

affiliations:
 - name: Sciences Po, Centre de données Socio-Politiques (CDSP), CNRS
   index: 1
date: 24 July 2023
---

# Summary

Web Panel Sample Service (WPSS) is a web application integrated with the Qualtrics survey platform, designed specifically to address the needs of cross-national longitudinal web surveys. WPSS enables centralized management of survey fieldwork tasks based on user roles (publishing, sending invites and reminders), while ensuring decentralized and privacy-compliant handling of panelist data. This service was successfully used by the ESS ERIC (European Social Survey, supported by a European Research Infrastructure Consortium or ERIC) from 2021 to 2023 for the CRONOS2 study ("The CROss-National Online Survey, second edition") and is equally applicable to similar use cases. Comprehensive user documentation for the CRONOS2 use case is available online at <https://cdsp-scpo.github.io/wpss-doc/>

# Statement of need

Cross-national web surveys are critical tools in research, especially within the Social Sciences and Humanities. These surveys enable the collection of harmonized data across multiple countries, providing valuable insights into comparative social phenomena. However, managing such complex surveys presents significant challenges, particularly in terms of efficiently handling respondent samples, ensuring accurate translation and distribution of questionnaires, and maintaining compliance with strict data protection regulations like the GDPR.

Challenges and WPSS Solutions:

- Managing Respondent Samples: In large-scale studies, coordinating respondent data across multiple countries can be daunting. WPSS facilitates this by enabling centralized management of respondent contact data, while still allowing decentralized handling to ensure privacy compliance. This dual approach simplifies the complex logistics of cross-national studies.

- Flexible Communication: Traditional survey platforms often lack the flexibility needed for multi-modal communication. For example, a study coordinator might want to send an initial email invitation followed by an SMS reminder. WPSS, integrated with Qualtrics via its API, overcomes this limitation by offering a customizable messaging system that adapts to various communication strategies, thereby maximizing response rates.

- Data Protection Compliance: Ensuring GDPR compliance is paramount in cross-national surveys. WPSS minimizes data flows and ensures that personal contact data and survey data are encrypted and accessible only to authorized roles. This feature is particularly critical in maintaining the trust of respondents and the integrity of the study.

## Use Case Examples:

- Use Case 1: In a European  Study , a research team need to distribute surveys in multiple languages across 15 countries. WPSS enable them to design, translate, and distribute the survey through a combination of emails and SMS, achieving a higher response rate compared to previous methodologies.

- Use Case 2: A survey conducted across different age groups in the GGP required strict data protection measures due to the sensitivity of the information collected. WPSS ensure that all data are encrypted and managed according to GDPR standards, while also providing real-time dashboards for monitoring the progress of the survey.

# Mentions

WPSS has been used by the "The CROss-National Online Survey, second version" led by the European Social Survey ERIC (European Research Infrastructure Consortium). All data produced available as FAIR and open data at the ESS ERIC data dissemination portal: <https://ess-search.nsd.no/>

# Acknowledgements

This project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreements No 871063 [DOI:10.3030/871063](https://doi.org/10.3030/871063) and No 823782 [DOI:10.3030/823782](https://doi.org/10.3030/823782).

# References
Rory Fitzgerald, Gianmaria Bottoni, Curtis Jessop, Øyvind Straume, Quentin Agren, Geneviève Michaud, & Nicolas Sauger. (2019). SSHOC D4.1 A sample management system for cross- national web survey (V2.6). Zenodo. <https://doi.org/10.5281/zenodo.4436727>

Bottoni, G., (2023). CROss-National Online Survey 2 (CRONOS-2) panel data and documentation user guide. London: ESS ERIC. <https://stessrelpubprodwe.blob.core.windows.net/data/cronos2/CRON2_user_guide_e01_0.pdf>

Didrik Finnøy (ESS NSD), Bjørn-Ole Johannesen (ESS NSD), Erlend Aarsand (ESS NSD), Ana Villar (ESS HQ/CITY), Elena Sommer (ESS HQ/CITY). (2017). SERISS (synergies for Europe's research infrastructures in the social sciences) Database system for panel administration. <https://seriss.eu/wp-content/uploads/2018/04/SERISS_Deliverable-7.9_Panel_administration_database_FINAL.pdf>

Elena Sommer (ESS HQ/CITY), Ana Villar (ESS HQ/CITY), Didrik Finnøy (ESS NSD), Bjørn-Ole Johannesen (ESS NSD), Erlend Aarsand (ESS NSD). (2017). SERISS (synergies for Europe's research infrastructures in the social sciences) Web survey platform. <https://seriss.eu/wp-content/uploads/2018/04/SERISS_Deliverable_7.10_Web-survey-tool.pdf>

Quatrics API reference, online, <https://api.qualtrics.com/0f8fac59d1995-api-reference>
