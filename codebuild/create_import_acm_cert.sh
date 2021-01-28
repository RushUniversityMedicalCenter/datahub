# Copyright 2019-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/bin/bash

#set -x

echo "List existing certs"
aws acm list-certificates --output text

if [ $(aws acm list-certificates --output text|grep fhirconv.selfsigned.com|wc -l) -gt 0 ]; then
    echo "Self-signed certificate already imported"
    SELF_SIGNED_CERT_ACM_ARN=$(aws acm list-certificates --output text|grep fhirconv.selfsigned.com|head -1|awk '{print $2}')
    #aws ssm put-parameter --name "/${envName}/fhirConv/self_signed_acm_arn" --value ${SELF_SIGNED_CERT_ACM_ARN} --type String --overwrite

else
    echo "Certificate not found. Generating self-signed certificate and importing into ACM"
    openssl genrsa 2048 > privatekey.pem
    openssl req -new -x509 -key privatekey.pem -out certificate.pem -days 3650 -subj /CN=fhirconv.selfsigned.com
    aws acm import-certificate --certificate fileb://certificate.pem --private-key fileb://privatekey.pem
    SELF_SIGNED_CERT_ACM_ARN=$(aws acm list-certificates --output text|grep fhirconv.selfsigned.com|head -1|awk '{print $2}')
    aws ssm put-parameter --name "/${envName}/fhirConv/self_signed_acm_arn" --value ${SELF_SIGNED_CERT_ACM_ARN} --type String --overwrite
fi

