# Copyright (c) 2022 Juha Toivola
# Licensed under the terms of the MIT License

import json
import urllib3
import certifi
import arcpy


# custom exception if there is an error sending a message
class SendLocationToWhatsAppException(Exception):
    error_msg = ""

    def __init__(self, error_msg, *args):
        super().__init__(args)
        self.error_msg = error_msg

    def __str__(self):
        return 'Exception: ' + self.error_msg


# This is used to execute code if the file was run but not imported
if __name__ == '__main__':
    # Tool parameter accessed with GetParameter or GetParameterAsText
    point = arcpy.GetParameterAsText(0)

    count_point_fc = int(arcpy.GetCount_management(point).getOutput(0))
    if count_point_fc == 0:
        raise SendLocationToWhatsAppException("Input point feature class contains no records")
    if count_point_fc > 1:
        raise SendLocationToWhatsAppException("Input point feature class must contain only one record")

    location_name = arcpy.GetParameterAsText(1)

    msg = arcpy.GetParameterAsText(2)

    recipient_phone_number = arcpy.GetParameterAsText(3)  # phone number to send message to
    access_token = arcpy.GetParameterAsText(4) # temporary access token

    phone_number_id = arcpy.GetParameterAsText(5)  # meta provided test phone number id

    tmp = arcpy.env.scratchGDB

    input_spatial_ref = arcpy.Describe(point).spatialReference
    if input_spatial_ref.factoryCode != 4326:
        conversion_method = None
        if "North American 1984" in input_spatial_ref.datumName:
            conversion_method = "NAD_1983_To_WGS_1984_5"
        wgs_84 = arcpy.SpatialReference(4326)
        tmp_point = tmp + "/tmp_point"
        arcpy.management.Project(point, tmp_point, wgs_84, transform_method=conversion_method)
        point = tmp_point

    with arcpy.da.SearchCursor(point, "SHAPE@XY") as cursor:
        for row in cursor:
            x = row[0][0]
            y = row[0][1]
            break

    data = {
        'messaging_product': 'whatsapp',
        'to': recipient_phone_number,
        'type': 'location',
        "location": {
            "longitude": str(x),
            "latitude": str(y),
            "name": location_name
        }
    }

    url = f"https://graph.facebook.com/v13.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        'Content-Type': 'application/json'
    }
    data = json.dumps(data)
    encoded_data = data.encode('utf-8')
    headers = json.dumps(headers)

    http = urllib3.PoolManager(ca_certs=certifi.where())

    resp = http.request(
        'POST',
        url,
        body=encoded_data,
        headers={"Authorization": f"Bearer {access_token}", 'Content-Type': 'application/json'})

    resp_content = json.loads(resp.data.decode('utf-8'))

    if resp.status != 200:
        err_msg = resp_content['error']['message']
        arcpy.AddWarning(f"HTTP response status: {resp.status} - {resp.reason} - {err_msg}")
    else:
        arcpy.AddMessage(f"HTTP response status: {resp.status} - {resp.reason}")

    if msg:
        msg_data = {
            'messaging_product': 'whatsapp',
            'to': recipient_phone_number,
            'type': 'text',
            "text": {
                "body": msg
            }
        }

        msg_data = json.dumps(msg_data)
        encoded_msg_data = msg_data.encode('utf-8')

        msg_resp = http.request(
            'POST',
            url,
            body=encoded_msg_data,
            headers={"Authorization": f"Bearer {access_token}", 'Content-Type': 'application/json'})

        msg_resp_content = json.loads(resp.data.decode('utf-8'))

        if msg_resp.status != 200:
            msg_err_msg = msg_resp_content['error']['message']
            arcpy.AddWarning(f"HTTP response status: {msg_resp.status} - {msg_resp.reason} - {msg_err_msg}")
        else:
            arcpy.AddMessage(f"HTTP response status: {msg_resp.status} - {msg_resp.reason}")
