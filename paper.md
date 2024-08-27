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

Cross-national web surveys are crucial for research, particularly in the Social Sciences and Humanities. Collecting data through online surveys is an efficient method, both in terms of cost and time, especially when compared to alternatives like interviews. These surveys are often conducted within harmonized and comparative studies, such as SHARE (Survey of Health, Ageing and Retirement in Europe), GGP (Generations and Gender Programme), EVS (European Values Study), or Pew Research Center international surveys.

However, managing such surveys presents several challenges:

    Respondent Sample Management: Importing, managing, and exporting respondents' contact data.
    Questionnaire Design and Translation: Designing and translating questionnaires, as well as drafting and translating messages.
    Questionnaire Distribution: Distributing questionnaires to respondents using messages, ensuring they receive the correct language version.
    Panelist Access: Respondents should have access to a web application, known as the "panelist portal," where they can complete the questionnaires.

While existing survey platforms provide some of these features, they often lack flexibility, particularly in terms of contact mode management. For example, study coordinators may wish to alternate between sending email invitations and SMS reminders, a feature not commonly available on most platforms (Fitzgerald et al., 2019). Additionally, centralized dashboards are essential for monitoring study progress, including message delivery performance and survey completion rates.

To address these needs, WPSS was developed as a complementary web application that integrates with Qualtrics via its API. WPSS enhances the capabilities of the survey platform by offering flexible messaging modes, global dashboards, and strict control over personal data, ensuring compliance with the General Data Protection Regulation (GDPR). This includes minimizing data flows and ensuring that both survey and contact data are encrypted and accessible only to authorized roles.

By focusing on these aspects, WPSS effectively meets the complex demands of cross-national web surveys, providing significant value to researchers in this field.

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
