# Survey monitoring

## Overview

To view a list of surveys that have been published to your assigned sample, select the `Individual links` card.

![Message delivery card](../img/nc/individual-links-card.png)

![Individual links overview](../img/nc/nc-individual-links-overview.png)

Select the blue `Details` button to display the panelists for whom an individual link has been created, as well as a (bright) color indicating the response status (`red` as not started, `yellow` as started and `green` as finished).

![Individual links details](../img/nc/nc-individual-links-detail.png)

Results can be filtered by study ID (ESS ID) by clicking the `Filters` grey button.

| Category                                                                         | Notes                                                                                                                                                                                                                                 |
|----------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <span style="color:#DD3B4B;font-weight:bold">Not Started</span>                  | Panelist did not start the survey                                                                                                                                                                                                     |
| <span style="color:#FFC720;font-weight:bold">Started</span>                      | Panelist started the survey, but did not complete it.<br/>The survey deadline still allows him/her to finish the survey                                                                                                               |
| <span style="color:#DD3B4B;font-weight:bold;opacity:75%">Partially Finished</span> | Panelist started the survey, but did not complete it.<br/>The survey deadline no longer allows him/her to finish the survey.<br/>His/her responses are recorded                                                                             |
| <span style="color:#2B9061;font-weight:bold">Finished</span>                       | Panelist completed the survey by answering all questions                                                                                                                                                                              |


![Individual links details filter on](../img/nc/filters-on.png)

A red dot idicates a filter is active. The blue label shows the total sample size and records filtered.
To deactivate a filter, click the `Reset`button.

Results can be browsed page by page using the pagination at the bottom of each page.

![Individual links details pagination](../img/nc/paginator.png)

## Exporting response statuses ##

To get individual response status as a CSV file, click on the grey `Export response statuses` button

![Response statuses button](../img/nc/nc-export-response-status-button.png)

You will get a two-columns CSV file, one record for each person in your assigned sample:

`ess_id`

: as defined [here](./sample-import-export-fields.md#idno)

`status`

: values being one of:

     `Pending`

     : panelist did not yet enter the survey

     `SurveyStarted`

     : panelist did enter the survey

    `SurveyPartiallyFinished`

    : panelist started the survey but did not finish it and cannot return to it because the survey deadline is over (see [survey parameters](../survey/survey-creation.md#mandatory-manage-partial-responses))

     `SurveyFinished`

     : panelist completed the survey
