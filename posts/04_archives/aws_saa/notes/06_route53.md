# Route53
- Domain/subdomain
- Record type (A, AAAA, CNAME, NS)
    - A: IPv4
	- AAAA: IPv6
	- CNAME: Canonical name. cant be used for root domain
	- NS: Name server (another DNS server)
	- alias: Route53 specific. can be used for root domain. free. health check. no TTL, can't be used for ec2 instance
- Value
- Routing policy
	- Simple: one record with multiple values, choose randomly by client, no health check, if alias then specify only one
	- Weighted: split traffic based on weight
	- Latency based: split traffic based on latency
	- Failover: primary and secondary
	- Geolocation
	- Multivalue answer: multiple values, health check, choose randomly by client
	- Geo-proximity
- TTL

## health check
- Endpoint
- Calculated
- CloudWatch alarm