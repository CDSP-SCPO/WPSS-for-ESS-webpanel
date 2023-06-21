# -- STDLIB
from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock, call, patch

# -- QXSMS (LOCAL)
from .. import client


class HelpersTestCase(TestCase):

    def test_urljoin_relative(self):
        parts = ['https://foo.eu/', 'bar/', '/baz']
        result = client._urljoin(*parts)
        expected = 'https://foo.eu/bar/baz'
        self.assertEqual(result, expected)

    def test_urljoin_absolute(self):
        parts = ['https://foo.eu/', 'https://buff.eu', 'bar/', '/baz']
        result = client._urljoin(*parts)
        expected = 'https://buff.eu/bar/baz'
        self.assertEqual(result, expected)

    @patch('time.sleep')
    def test_poll_success(self, sleep_func: Mock):
        target = Mock()
        # Repeated calls will return these values in succession
        target.side_effect = [False, False, False, True]
        val = client._poll(target=target, step=1)
        self.assertTrue(val)
        expected_calls = [call(1), call(2), call(4)]
        self.assertListEqual(sleep_func.call_args_list, expected_calls)

    @patch('time.sleep')
    def test_poll_max_tries_exceeded(self, sleep_func):
        target = Mock()
        target.side_effect = [False, False, False, True]
        with self.assertRaises(TimeoutError):
            client._poll(target=target, step=1, max_tries=3)
        expected_calls = [call(1), call(2)]
        self.assertListEqual(sleep_func.call_args_list, expected_calls)

    def test_poll_max_tries_positive(self):
        with self.assertRaises(AssertionError):
            client._poll(target=lambda: True, step=1, max_tries=0)

    def test_is_complete(self):
        self.assertTrue(client._is_complete({'status': 'complete'}))
        self.assertFalse(client._is_complete({'status': 'pending'}))

    def test_parse_datetime(self):
        expected = datetime(2021, 5, 5, 15, 0, 0)
        self.assertEqual(client.parse_datetime("2021-05-05T15:00:00Z"), expected)
        self.assertEqual(client.parse_datetime("2021-05-05T15:00:00.000Z"), expected)
        self.assertEqual(client.parse_datetime("2021-05-05 15:00:00"), expected)
        self.assertIsNone(client.parse_datetime("wrong"))

    def test_format_datetime(self):
        dt = datetime(2021, 5, 5, 15, 0, 0)
        self.assertEqual(client.format_datetime(dt, iso=True), "2021-05-05T15:00:00Z")
        self.assertEqual(client.format_datetime(dt, iso=False), "2021-05-05 15:00:00")


class ContactImportManagerTestCase(TestCase):

    @patch('time.sleep')
    def test_wait_until_complete(self, sleep_func):
        xm = Mock()
        xm.get.side_effect = [{'status': 'pending'}, {'status': 'complete', 'sentinel': ''}]
        ci = client.ContactImportManager(client=xm, directory_id='DIR', list_id='ML')
        result = ci.wait_until_complete('foo', step=1)
        self.assertIsNotNone(result.get('sentinel'))
        self.assertEqual(len(xm.get.call_args_list), 2)

    def test_import_empty_contacts_list(self):
        xm = Mock()
        ci = client.ContactImportManager(client=xm, directory_id='DIR', list_id='ML')
        self.assertRaises(client.QxClientError, ci.start_import, [])


class DistributionTestCase(TestCase):

    def test_email_distribution_spec(self):
        expected = {
            "header": {
                "fromEmail": "FROM_EMAIL",
                "fromName": "FROM_NAME",
                "replyToEmail": "REPLY_TO",
                "subject": "SUBJECT_ID"
            },
            "message": {
                "libraryId": "LIBRARY_ID",
                "messageId": "MESSAGE_ID"
            },
            "recipients": {
                "transactionBatchId": "BATCH_ID"
            },
            'surveyLink': {
                "surveyId": "SURVEY_ID",
                "expirationDate": "2021-05-06T11:20:00Z",
                "type": "Anonymous"
            },
            "sendDate": "2021-05-05T11:20:00Z"
        }
        result = client._email_distribution_spec(from_email="FROM_EMAIL", from_name="FROM_NAME",
                                                 reply_to="REPLY_TO", subject_id="SUBJECT_ID",
                                                 library_id="LIBRARY_ID", message_id="MESSAGE_ID",
                                                 batch_id="BATCH_ID", survey_id="SURVEY_ID",
                                                 link_type='Anonymous',
                                                 link_expiration_date=datetime(2021, 5, 6, 11, 20, 0),
                                                 send_date=datetime(2021, 5, 5, 11, 20, 0))

        # Compare nested dicts separately for more granular failure diffs
        for key in ('header', 'message', 'recipients', 'surveyLink'):
            self.assertDictEqual(result.get(key), expected.get(key))
        self.assertEqual(result.get('sendDate'), expected.get('sendDate'))

        with self.assertRaises(ValueError):
            client._email_distribution_spec(from_email="FROM_EMAIL", from_name="FROM_NAME",
                                            reply_to="REPLY_TO", subject_id="SUBJECT_ID",
                                            library_id="LIBRARY_ID", message_id="MESSAGE_ID",
                                            batch_id="BATCH_ID", survey_id="SURVEY_ID",
                                            # Invalid link type
                                            link_type='Invalid',
                                            link_expiration_date=datetime(2021, 5, 6, 11, 20, 0),
                                            send_date=datetime(2021, 5, 5, 11, 21, 0))

    @patch('distributions.client.datetime')
    @patch('distributions.client.DEFAULT_LINK_EXPIRATION_DAYS', 1)
    def test_send_defaults(self, mock_dt):
        xm = Mock()
        xm.library_id = "LIBRARY_ID"
        dm = client.DistributionManager(client=xm)
        expected = {
            "header": {
                "fromEmail": "FROM_EMAIL",
                "fromName": "FROM_NAME",
                "replyToEmail": "REPLY_TO",
                "subject": "SUBJECT_ID"
            },
            "message": {
                "libraryId": "LIBRARY_ID",
                "messageId": "MESSAGE_ID"
            },
            "recipients": {
                "transactionBatchId": "BATCH_ID"
            },
            'surveyLink': {
                "surveyId": "SURVEY_ID",
                "expirationDate": "2021-05-06T11:20:00Z",
                "type": "Anonymous"
            },
            "sendDate": "2021-05-05T11:20:00Z"
        }
        mock_dt.now.return_value = datetime(2021, 5, 5, 11, 20, 0)
        dm.send(from_email="FROM_EMAIL", from_name="FROM_NAME",
                reply_to="REPLY_TO", subject_id="SUBJECT_ID",
                library_id="LIBRARY_ID", message_id="MESSAGE_ID",
                batch_id="BATCH_ID", survey_id="SURVEY_ID",
                link_type='Anonymous')
        xm.post.assert_called_with(dm.path, json_data=expected)


class SMSDistributionTestCase(TestCase):

    def test_sms_distribution_spec(self):
        expected = {
            "name": "NAME",
            "surveyId": "SURVEY_ID",
            "method": "Invite",
            "message": {
                "messageId": "MESSAGE_ID",
                "libraryId": "LIBRARY_ID"
            },
            "sendDate": "2021-05-05T14:00:00Z",
            "recipients": {
                "transactionBatchId": "BATCH_ID"
            }
        }
        result = client._sms_distribution_spec(
            name="NAME",
            survey_id="SURVEY_ID",
            message_id="MESSAGE_ID",
            library_id="LIBRARY_ID",
            send_date=datetime(2021, 5, 5, 14, 0, 0),
            batch_id="BATCH_ID"
        )
        self.assertDictEqual(result, expected)

    @patch('distributions.client.datetime')
    def test_send_defaults(self, dt_mock):
        dt_mock.now.return_value = datetime(2021, 5, 5, 14, 0, 0)
        expected = {
            "name": "NAME",
            "surveyId": "SURVEY_ID",
            "method": "Invite",
            "message": {
                "messageId": "MESSAGE_ID",
                "libraryId": "LIBRARY_ID"
            },
            "sendDate": "2021-05-05T14:00:00Z",
            "recipients": {
                "transactionBatchId": "BATCH_ID"
            }
        }
        xm = Mock()
        xm.library_id = "LIBRARY_ID"
        dm = client.SMSDistributionManager(client=xm)
        dm.send(
            name="NAME",
            survey_id="SURVEY_ID",
            message_id="MESSAGE_ID",
            batch_id="BATCH_ID"
        )
        xm.post.assert_called_with(dm.path, json_data=expected)
