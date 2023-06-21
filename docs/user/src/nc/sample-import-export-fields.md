# Sample file specifications

## Import fields

Default values are applied when the values are left empty.

### idno
ESS Panelist identification number (ESS IDNO).

>Required
>
>- Number (max length: 12)

### name

>Optional | Default: empty
>
>- Free text

### surname

>Optional | Default: empty
>
>- Free text

### sex

>Required
>
>- `1` ➜ Male
>- `2` ➜ Female
>- `3` ➜ Other
>- `7` ➜ Refusal
>- `8` ➜ Don't know
>- `9` ➜ No answer

### email
Panelist email address.

>Required if `mobile` is empty | Default: empty
>
>- Email address. It is used by panelists to (optionnally) login to WPSS. It is case sensitive.


### mobile
Panelist mobile phone number.

>Required if `email` is empty | Default: empty
>Text format of the form: `+` `XX` `YYYYYYYYYY` where
>
>- `XX` is the country calling code
>- `YYYYYYYYYY` is the mobile phone number without trailing zero
>
>e.g. `+442012345677`

### propertyname
Name of Property.

>Optional | Default: empty
>
>- Free text

### number

>Optional | Default: empty
>
>- Free text

### address

>Optional | Default: empty
>
>- Free text

### address2

>Optional | Default: empty
>
>- Free text

### city

>Optional | Default: empty
>
>- Free text

### county

>Optional | Default: empty
>
>- Free text

### postcode

>Optional | Default: empty
>
>- Free text

### cntry
Country code.

>Required
>
>- `AT` ➜ Austria
>- `BE` ➜ Belgium
>- `BG` ➜ Bulgaria
>- `CZ` ➜ Czechia
>- `HR` ➜ Croatia
>- `CY` ➜ Cyprus
>- `EE` ➜ Estonia
>- `FI` ➜ Finland
>- `FR` ➜ France
>- `DE` ➜ Germany
>- `HU` ➜ Hungary
>- `IS` ➜ Iceland
>- `IE` ➜ Ireland
>- `IT` ➜ Italy
>- `LV` ➜ Latvia
>- `LT` ➜ Lithuania
>- `NL` ➜ The Netherlands
>- `NO` ➜ Norway
>- `PL` ➜ Poland
>- `PT` ➜ Portugal
>- `SK` ➜ Slovakia
>- `SI` ➜ Slovenia
>- `SE` ➜ Sweden
>- `GB` ➜ United Kingdom
>- `CH` ➜ Switzerland
>- `AL` ➜ Albania
>- `DK` ➜ Denmark
>- `IL` ➜ Israel
>- `ME` ➜ Montenegro
>- `RS` ➜ Serbia
>- `ES` ➜ Spain
>- `GR` ➜ Greece
>- `XK` ➜ Kosovo
>- `LU` ➜ Luxembourg
>- `RO` ➜ Romania
>- `RU` ➜ Russia
>- `TK` ➜ Turkey
>- `UA` ➜ Ukraine

### lng
Panelist language [code](https://www.qualtrics.com/support/survey-platform/survey-module/survey-tools/translate-survey/#AvailableLanguageCodes).

>Required
>
>- `CS` ➜ Czech
>- `DE` ➜ German
>- `EN` ➜ English
>- `FI` ➜ Finnish
>- `FR` ➜ French
>- `BE-FR` ➜ French (Belgium)
>- `HU` ➜ Hungarian
>- `ISL` ➜ Icelandic
>- `IT` ➜ Italian
>- `SL` ➜ Slovenian
>- `SV` ➜ Swedish
>- `FI-SV` ➜ Swedish (Finland)
>- `PT` ➜ Portuguese
>- `BE-NL` ➜ Flemish (Belgium)
>- `ISL-PL` ➜ Polish (Island)

### netusoft
Internet use, how often.

>Required
>
>- `1` ➜ Never
>- `2` ➜ Only occasionally
>- `3` ➜ A few times a week
>- `4` ➜ Most days
>- `5` ➜ Every day
>- `7` ➜ Refusal
>- `8` ➜ Don't know
>- `9` ➜ No answer

### eduyrs
Years of full-time education completed.

>Required
>
>- `77` Refusal
>- `88` Don't know
>- `99` No answer

### dybrn
Day of birth.

>Required
>
>- Value between `1` and `31`
>- `77` ➜ Refusal
>- `88` ➜ Don't know
>- `99` ➜ No answer

### mthbrn
Month of birth.

>Required
>
>- Value between `1` and `12`
>- `77` ➜ Refusal
>- `88` ➜ Don't know
>- `99` ➜ No answer

### yrbrn
Year of birth.

>Required
>
>- Value between `1905` and `2005`
>- `7777` ➜ Refusal
>- `8888` ➜ Don't know
>- `9999` ➜ No answer

### opto
Panelist opted out.

If set to `1` or checked in WPSS, individual links will no longer be generated for this panelist and no messages will be sent to them. If changed back to `0` or unchecked in WPSS, the panelist will be able to participate to next surveys (when new individual links are generated for them).

>Optional | Default: `0`
>
>- `0` ➜ do nothing or opts the panelist in if they were out
>- `1` ➜ opts the panelist out

### dopto
Date panelist opted out.

>Optional if `is_opt_out` is `0` | Default: empty
>
>- Date (format: `DDMMYYYY`)

### ropto
Reason(s) why panelist opts out.

>Optional if `is_opt_out` is `0` | Default: empty
>
>- Free text

### delcontactdata
Panelist requests contact data to be deleted.

>Optional | Default: `0`
>
>- `0` ➜ do nothing
>- `1` ➜ the panelist asked to delete their data

### delsurveydata
Panelist requests survey data to be deleted.

>Optional | Default: `0`
>
>- `0` ➜ do nothing
>- `1` ➜ the panelist asked to delete their data

### movcntry
Panelist moved out of country.

>Optional | Default: `0`
>
>- `0` ➜ do nothing
>- `1` ➜ the panelist is out of the country

### noincen
Panelist does not want incentives.

>Optional | Default: `0`
>
>- `0` ➜ do nothing
>- `1` ➜ the panelist does not want incentives

### nolett
Panelist does not want letters.

>Optional | Default: `0`
>
>- `0` ➜ do nothing
>- `1` ➜ the panelist does not want to receive letters

### notxt
Panelist does not want text messages.

>Optional | Default: `0`
>
>- `0` ➜ do nothing
>- `1` ➜ the panelist does not want to receive text messages

### noem
Panelist does not want emails.

>Optional | Default: `0`
>
>- `0` ➜ do nothing
>- `1` ➜ the panelist does not want to receive emails


## Export fields

The export fields are the same as the import fields. However there is an option to export with additional variables that are the following.

### dob
Date of birth.

>Format: DDMMYYYY

### age
Age of respondent (calculated).

>- 999 ➜ Not available

### agegrp
Age group of respondent.

>- `1` ➜ 18-24
>- `2` ➜ 25-34
>- `3` ➜ 35-44
>- `4` ➜ 45-54
>- `5` ➜ 55-64
>- `6` ➜ 65-74
>- `7` ➜ 75+
>- `9` ➜ Not available

### uid
Computed variable.

>- Concatenation of `cntry` and `ess_id`

### emailpres
Email address present in sample file.

>- `0` ➜ not present
>- `1` ➜ present

### mobilepres
Mobile phone number present in sample file.

>- `0` ➜ not present
>- `1` ➜ present

### addresspres
Address present in sample file.

>- `0` ➜ not present
>- `1` ➜ present

### anonsince
Date of anonymization.

### falseemail
If the email is false (result of anonymization).

>- `0` ➜ not false
>- `1` ➜ false

### panel
Panel name ([as set by study coordinators](../hq/seeding-a-study.md#creating-samples)).
