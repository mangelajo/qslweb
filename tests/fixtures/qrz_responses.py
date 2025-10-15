"""
Mock QRZ API responses for testing.

These responses are based on real QRZ API output but with anonymized personal information.
"""

# URL-encoded ADIF response (this is what QRZ actually returns)
SAMPLE_ADIF_RESPONSE = """RESULT=OK&COUNT=3&ADIF=&lt;qrzcom_qso_download_date:8&gt;20251015
&lt;my_cq_zone:2&gt;14
&lt;eqsl_qslrdate:8&gt;00000000
&lt;my_iota:4&gt;none
&lt;qrzcom_qso_download_status:1&gt;Y
&lt;eqsl_qslsdate:8&gt;00000000
&lt;station_callsign:6&gt;W1TEST
&lt;my_city:7&gt;Anytown
&lt;my_itu_zone:2&gt;37
&lt;eqsl_qsl_rcvd:1&gt;N
&lt;my_name:8&gt;John Doe
&lt;lotw_qsl_rcvd:1&gt;N
&lt;lotw_qsl_sent:1&gt;Y
&lt;qrzcom_qso_upload_date:8&gt;20250731
&lt;my_country:13&gt;United States
&lt;freq_rx:6&gt;438.95
&lt;my_lat:11&gt;N040 49.189
&lt;tx_pwr:1&gt;8
&lt;dxcc:3&gt;291
&lt;qsl_rcvd:1&gt;N
&lt;lotw_qslrdate:8&gt;00000000
&lt;qsl_via:4&gt;eQSL
&lt;app_qrzlog_status:1&gt;N
&lt;lotw_qslsdate:8&gt;20251010
&lt;comment:10&gt;Test QSO 1
&lt;mode:2&gt;FM
&lt;name:10&gt;Jane Smith
&lt;qth:8&gt;Anywhere
&lt;country:13&gt;United States
&lt;my_lon:11&gt;W073 38.204
&lt;lat:11&gt;N040 17.751
&lt;qso_date_off:8&gt;20250730
&lt;eqsl_qsl_sent:1&gt;N
&lt;gridsquare:6&gt;FN30gh
&lt;band:4&gt;70cm
&lt;cont:2&gt;NA
&lt;my_state:2&gt;NY
&lt;my_gridsquare:6&gt;FN30et
&lt;qso_date:8&gt;20250730
&lt;time_on:4&gt;2100
&lt;freq:6&gt;438.95
&lt;band_rx:4&gt;70cm
&lt;app_qrzlog_logid:10&gt;1301863042
&lt;call:6&gt;K2TEST
&lt;ituz:2&gt;08
&lt;distance:2&gt;61
&lt;lon:11&gt;W073 26.504
&lt;email:16&gt;test@example.com
&lt;cqz:2&gt;05
&lt;time_off:4&gt;2100
&lt;qsl_sent:1&gt;N
&lt;qrzcom_qso_upload_status:1&gt;Y
&lt;eor&gt;

&lt;gridsquare:6&gt;FN31dj
&lt;eqsl_qsl_sent:1&gt;N
&lt;band:3&gt;20m
&lt;cont:2&gt;NA
&lt;my_state:2&gt;NY
&lt;lotw_qslsdate:8&gt;20251010
&lt;name:12&gt;Bob Johnson
&lt;mode:3&gt;SSB
&lt;qth:8&gt;Testtown
&lt;comment:10&gt;Test QSO 2
&lt;country:13&gt;United States
&lt;my_lon:11&gt;W073 38.204
&lt;qso_date_off:8&gt;20250803
&lt;lat:11&gt;N041 22.802
&lt;ituz:2&gt;08
&lt;lon:11&gt;W073 44.121
&lt;distance:2&gt;50
&lt;cqz:2&gt;05
&lt;email:16&gt;test2@sample.com
&lt;qsl_sent:1&gt;N
&lt;time_off:4&gt;1530
&lt;qrzcom_qso_upload_status:1&gt;Y
&lt;my_gridsquare:6&gt;FN30et
&lt;time_on:4&gt;1530
&lt;qso_date:8&gt;20250803
&lt;freq:5&gt;14.25
&lt;band_rx:3&gt;20m
&lt;call:6&gt;N3TEST
&lt;app_qrzlog_logid:10&gt;1301863981
&lt;station_callsign:6&gt;W1TEST
&lt;eqsl_qslsdate:8&gt;00000000
&lt;my_city:7&gt;Anytown
&lt;my_itu_zone:2&gt;08
&lt;eqsl_qsl_rcvd:1&gt;N
&lt;qrzcom_qso_download_date:8&gt;20251015
&lt;my_cq_zone:2&gt;05
&lt;eqsl_qslrdate:8&gt;00000000
&lt;my_iota:4&gt;none
&lt;qrzcom_qso_download_status:1&gt;Y
&lt;tx_pwr:2&gt;50
&lt;my_lat:11&gt;N040 49.189
&lt;dxcc:3&gt;291
&lt;qsl_rcvd:1&gt;N
&lt;lotw_qslrdate:8&gt;00000000
&lt;app_qrzlog_status:1&gt;N
&lt;iota:4&gt;none
&lt;my_name:8&gt;John Doe
&lt;lotw_qsl_rcvd:1&gt;N
&lt;lotw_qsl_sent:1&gt;Y
&lt;qrzcom_qso_upload_date:8&gt;20250803
&lt;my_country:13&gt;United States
&lt;freq_rx:5&gt;14.25
&lt;rst_sent:2&gt;59
&lt;rst_rcvd:2&gt;57
&lt;eor&gt;

&lt;my_iota:4&gt;none
&lt;qrzcom_qso_download_status:1&gt;Y
&lt;eqsl_qslrdate:8&gt;00000000
&lt;qrzcom_qso_download_date:8&gt;20251015
&lt;my_cq_zone:2&gt;05
&lt;eqsl_qsl_rcvd:1&gt;N
&lt;my_itu_zone:2&gt;08
&lt;my_city:7&gt;Anytown
&lt;eqsl_qslsdate:8&gt;00000000
&lt;station_callsign:6&gt;W1TEST
&lt;my_country:13&gt;United States
&lt;freq_rx:6&gt;14.074
&lt;qrzcom_qso_upload_date:8&gt;20250818
&lt;lotw_qsl_sent:1&gt;Y
&lt;lotw_qsl_rcvd:1&gt;N
&lt;my_name:8&gt;John Doe
&lt;app_qrzlog_status:1&gt;N
&lt;qsl_via:20&gt;VIA BUREAU OR DIRECT
&lt;rst_sent:3&gt;+10
&lt;qsl_rcvd:1&gt;N
&lt;lotw_qslrdate:8&gt;00000000
&lt;dxcc:3&gt;291
&lt;tx_pwr:2&gt;20
&lt;rst_rcvd:3&gt;-05
&lt;my_lat:11&gt;N040 49.189
&lt;my_state:2&gt;NY
&lt;cont:2&gt;NA
&lt;band:3&gt;20m
&lt;gridsquare:6&gt;FN31cb
&lt;eqsl_qsl_sent:1&gt;N
&lt;qso_date_off:8&gt;20250818
&lt;lat:11&gt;N041 03.700
&lt;my_lon:11&gt;W073 38.204
&lt;country:13&gt;United States
&lt;mode:3&gt;FT8
&lt;qth:8&gt;Testberg
&lt;name:11&gt;Alice Brown
&lt;comment:16&gt;My first FT8 QSO
&lt;lotw_qslsdate:8&gt;20251010
&lt;qrzcom_qso_upload_status:1&gt;Y
&lt;qsl_sent:1&gt;N
&lt;time_off:4&gt;0952
&lt;cqz:2&gt;05
&lt;distance:3&gt;142
&lt;lon:11&gt;W074 12.400
&lt;ituz:2&gt;08
&lt;call:5&gt;K4TST
&lt;app_qrzlog_logid:10&gt;1309164709
&lt;band_rx:3&gt;20m
&lt;freq:6&gt;14.074
&lt;time_on:4&gt;0952
&lt;qso_date:8&gt;20250818
&lt;my_gridsquare:6&gt;FN30et
&lt;eor&gt;
"""

# ADIF response with FAIL status
FAIL_ADIF_RESPONSE = """RESULT=FAIL&REASON=Invalid API key&COUNT=0"""

# ADIF response with no QSOs
EMPTY_ADIF_RESPONSE = """RESULT=OK&COUNT=0&ADIF="""
