# -- STDLIB
import argparse
from datetime import datetime
from urllib.parse import urljoin

# -- THIRDPARTY
import requests

DOMAIN = "https://fra1.qualtrics.com/API/v3/"


def get_opt_out_status(contact):
    """Returns the opt out status of a contact, with the dates."""

    opt_out = False
    opt_out_timestamps = []
    opt_out_dates = []

    # Check directory level status
    if contact['directoryUnsubscribed']:
        opt_out = True
        opt_out_timestamps.append(contact['directoryUnsubscribeDate'])

    # Check mailing list level statuses
    for ml in contact['mailingListMembership'].values():
        if ml['unsubscribed']:
            opt_out = True
            opt_out_timestamps.append(ml['unsubscribeDate'])

    # Transform timestamp into datetime
    for ts in opt_out_timestamps:
        # Qualtrics gives milliseconds since epoch, so we divide by 1000 for seconds
        opt_out_dates.append(datetime.fromtimestamp(ts / 1000))

    return {
        'opt_out': opt_out,
        'opt_out_dates': opt_out_dates if opt_out_dates else None,
    }


def get_contact(contact_id, api_key, directory_id):
    url = urljoin(DOMAIN, f'directories/{directory_id}/contacts/{contact_id}')
    res = requests.get(url, headers={'X-API-TOKEN': api_key}).json()
    try:
        contact = res['result']
        print(contact['embeddedData']['country'] + contact['embeddedData']['ess_id'])
        return {
            'country': contact['embeddedData']['country'],
            'ess_id': contact['embeddedData']['ess_id'],
            **get_opt_out_status(contact),
        }
    except Exception:
        print(res)


def main(args):
    contact_ids = args.list
    contacts = []
    for contact_id in contact_ids:
        contacts.append(get_contact(contact_id, args.key, args.directory))
    print(contacts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get ESS IDs from list of qualtrics Contact IDs.')
    parser.add_argument('-k', '--key', help='api key', required=True)
    parser.add_argument('-d', '--directory', help='directory ID', required=True)
    parser.add_argument('list', nargs='+', help='the list of contact IDs')
    args = parser.parse_args()
    main(args)
