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

WPSS stands for Web Panel Sample Service. It is a web application paired to Qualtrics survey platform to meet the specific needs of cross-national longitudinal web surveys.
WPSS enables a centralized management of survey fielding tasks based on user roles (publishing, sending invites and reminders), and a decentralized and privacy-compliant handling of panelist data. The service was used by the ESS ERIC (European Social Survey, supported by a European Research Infrastructure Consortium or ERIC) from 2021 to 2023, for the CRONOS2 study ("The CROss-National Online Survey, second edition"), but could be used in similar use cases. An extensive user documentation for the CRONOS2 use case is available online at https://cdsp-scpo.github.io/wpss-doc/.

# Statement of need

To fill the need of cross-national web surveys,
Researchers are in great demand of data collected through surveys, especially for the Social Sciences and Humanities. Online or web surveys are a way to start collecting data in an efficient way, regarding costs and time, compared for example to interviews. Online surveys are also conduced within harmonised and comparative studies such as SHARE, the Survey of Health, Ageing and Retirement in Europe, GGP, the Generations and Gender Programme, EVS, the European Values Study, or Pew Research Center international surveys.

The global service provided should allow to manage respondents samples (importing, managing and exporting respondents' contact data), design and translate questionnaires, draft and translate messages, distribute questionnaires to respondents using messages (both in relevant language version). Respondents should be able to connect to a web application to access questionnaires alternatively, a so-called "panelist portal".

A share of the features above can be provided by existing survey platform, the term "survey platform" refers to the software application used to design web questionnaires and publish them to a set of panellists that can use the platform to read the questions and then submit their answers online. There is no shortage of existing web survey platforms, generally, along with user-friendly questionnaire design tools, they allow study coordinators to manage lists of contacts to which surveys may be distributed through different communication channels, often emails and Short Text Messages. We selected Qualtrics, to be integrated using the Qualtrics API to a custom web application providing additional features.

To maximise survey response rates, study coordinators may want to freely intertwine contact modes during fieldwork: for example, sending an email invite followed by a Short Text Message reminder, or the other way round. This feature is commonly not available among available web survey platforms (Fitzgerald, Bottoni, Straume, Agren, Michaud and Sauger, 2019). The study coordination also needs centralised dashboards to monitor the study, getting an eagle-eye view of the study indicators related to messages delivery performance and survey completion (and response rates).
In addition, the service should comply with the General Data Protection Regulation (GDPR), a regulation in force in the European Union. Specifically, data flows should be minimised (either personal contact data or survey data). Data should be exchanged and stored encrypted, including on the survey patform. Survey data and contact data should be accessible only to distinct and authorized roles : on the survey platform.     

We focused on designing and providing a web application that would complement the chosen survey platform and provide the additional feature needed (message mode flexibility, global dashboards, personal data control, panelist portal).

# Mentions

WPSS has been used by the "The CROss-National Online Survey, second version" led by the European Social Survey ERIC (European Research Infrastructure Consortium). All data produced available as FAIR and open data at the ESS ERIC data dissemination portal: https://ess-search.nsd.no/.

# Acknowledgements

This project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreements No 871063. DOI:10.3030/871063 and No 823782 DOI:10.3030/823782.

# References
Rory Fitzgerald, Gianmaria Bottoni, Curtis Jessop, Øyvind Straume, Quentin Agren, Geneviève Michaud, & Nicolas Sauger. (2019). SSHOC D4.1 A sample management system for cross- national web survey (V2.6). Zenodo. https://doi.org/10.5281/zenodo.4436727

Bottoni, G., (2023). CROss-National Online Survey 2 (CRONOS-2) panel data and documentation user guide. London: ESS ERIC. https://stessrelpubprodwe.blob.core.windows.net/data/cronos2/CRON2_user_guide_e01_0.pdf

Didrik Finnøy (ESS NSD), Bjørn-Ole Johannesen (ESS NSD), Erlend Aarsand (ESS NSD), Ana Villar (ESS HQ/CITY), Elena Sommer (ESS HQ/CITY). (2017). SERISS (synergies for Europe's research infrastructures in the social sciences) Database system for panel administration. https://seriss.eu/wp-content/uploads/2018/04/SERISS_Deliverable-7.9_Panel_administration_database_FINAL.pdf

Elena Sommer (ESS HQ/CITY), Ana Villar (ESS HQ/CITY), Didrik Finnøy (ESS NSD), Bjørn-Ole Johannesen (ESS NSD), Erlend Aarsand (ESS NSD). (2017). SERISS (synergies for Europe's research infrastructures in the social sciences) Web survey platform. https://seriss.eu/wp-content/uploads/2018/04/SERISS_Deliverable_7.10_Web-survey-tool.pdf

Quatrics API reference, online, https://api.qualtrics.com/0f8fac59d1995-api-reference
