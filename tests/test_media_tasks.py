import json
from io import BytesIO
import unittest
from unittest.mock import patch

from lib import media_tasks


class TaskResults(unittest.TestCase):
    def test_api_shapes_and_markdown(self):
        url = 'https://example.com/media/item (1).png?x=y'
        for name, (_, kind, field) in media_tasks.SERVICES.items():
            with self.subTest(service=name):
                row = {field: url}
                result = {'task_id': 'example', 'data': [row, row]}
                if name == 'seedance':
                    result['data'] = {'content': row}
                if name == 'kling':
                    result.update(row)
                self.assertEqual(media_tasks.media_links(name, 'example', {'id': 'example', 'response': result}), [url])
                link = media_tasks.markdown(name, 0, url)
                self.assertIn('item%20(1).png'.replace('(', '%28').replace(')', '%29'), link)
                self.assertEqual(link.startswith('!'), kind == 'image')

    def test_task_identity_and_network_urls(self):
        for record in ({'id': 'other'}, {'id': 'id', 'response': {'task_id': 'other'}},
                       {'id': 'id', 'response': {'data': [{'image_url': 'file:///local'}]}},
                       {'id': 'id', 'response': {'data': [{'b64_json': 'encoded'}]}}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                media_tasks.media_links('seedream', 'id', record)

    def test_retrieve_request_stays_on_service(self):
        class Response(BytesIO):
            status = 200
        with patch('lib.media_tasks.http.client.HTTPSConnection') as connect:
            client = connect.return_value
            client.getresponse.return_value = Response(b'{"id":"owned"}')
            self.assertEqual(media_tasks.retrieve('suno', 'owned', 'fixture'), {'id': 'owned'})
            connect.assert_called_once_with('api.acedata.cloud', timeout=25)
            method, path, body, headers = client.request.call_args.args
            self.assertEqual((method, path), ('POST', '/suno/tasks'))
            self.assertEqual(json.loads(body), {'action': 'retrieve', 'id': 'owned'})
            self.assertEqual(headers['Authorization'], 'Bearer fixture')
            client.close.assert_called_once()
