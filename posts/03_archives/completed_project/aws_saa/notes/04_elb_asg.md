# ELB

## types of ELB

### Application Load Balancer (ALB):  
- HTTP, HTTPS, WebSockets  
- Layer 7
- `fixed hostname` in every AZ
- client IP address preservation in the `X-Forwarded-For` header
- can use `sticky sessions` through `cookies`
#### target group
- EC2 instances
- ECS tasks
- Lambda functions
- IP addresses (private)
#### routing
routing to diffrent target or same machine different application based on:
- routing based on URL
- routing based on hostname
- routing based on path
- routing based on query string
- routing based on HTTP header
- routing based on port

### Network Load Balancer (NLB):  
- TCP, TLS, UDP  
- Layer 4
- `fixed IP address` per AZ and support assigning Elastic IP address
- `high throughput` and `low latency`
#### target group
- EC2 instances
- IP addresses (private)
- Lambda functions
- ALB

### Gateway Load Balancer (GWLB):  
- ip
- Layer 3
- Deploy, scale, and manage third-party virtual appliances
- example: firewall, intrusion detection and prevention, deep packet inspection, and security analytics
- Transparent Network Gateway: single endpoint for all traffic
- Load Balancer Gateway: distribute traffic across multiple virtual appliances
- Use GENEVE tunneling protocol on port 6081
#### target group
- EC2 instances
- IP addresses (private)

## cross-zone load balancing
- distribute traffic evenly across all registered instances in all enabled AZs
- `enabled` by default for ALB and no charge for inter AZ data transfer (can be disabled in target group)
- `disabled` by default for NLB, GWLB and charge for inter AZ data transfer

## ssl/tls
### SNI
- Server Name Indication
- `ALB` and `NLB` and `cloudFront` support SNI

## Connection Draining
- `ALB` and `NLB` support connection draining (deregestration delay)

## ASG
### policy
- Target tracking scaling policy
- Simple / Step scaling policy
- Scheduled scaling policy
- Predictive scaling policy
