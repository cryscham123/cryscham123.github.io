## aws global infrastructure

### kind of infra
1. regions:  
cluster of data center
2. availability zone (AZ)
- usually 3, min 3, max 6
- one or more discrete data center
- separate from each others, so that isolated from disasters
3. Data center
- rack
- host
- instance
4. aws edge locations / points of presence  
: 400+ points of presence(400+ edge locations, 10+ regional cathes) in 90+ cities across 40+ contries

### global scope services, region scope services
1. global
- IAM
- DNS services
- CDN
- WAF

2. region
- ec2
- lambda
- rekognition

### how to choose region
1. compliance with data governance and legal requirements
2. proximity to customers
3. available services within a region
4. pricing
