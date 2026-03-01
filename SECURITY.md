# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Please do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. **Email**: Send a detailed report to the repository maintainers via the contact information in the GitHub profile of the repository owner.
2. **GitHub Security Advisories**: Use [GitHub's private vulnerability reporting](https://github.com/) feature if available on this repository.

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours of receiving your report
- **Assessment**: Within 7 days, we will assess the severity and impact
- **Fix**: Critical vulnerabilities will be addressed as soon as possible

### Scope

The following are in scope:
- Backend API (Python/Starlette/GraphQL)
- Frontend application (Vue.js)
- Authentication and authorization
- File upload/download handling
- AWS infrastructure configuration (CDK)

The following are out of scope:
- Issues in third-party dependencies (report these upstream)
- Denial of service attacks
- Social engineering

## Security Best Practices for Deployment

- Change the default admin password immediately after first deployment
- Set `DEBUG=false` in production (disables GraphiQL playground)
- Use a strong, unique `JWT_SECRET` value
- Configure a reverse proxy (e.g., nginx, ALB) with rate limiting
- Restrict CORS origins to your actual frontend domain via `FRONTEND_URL`
- Keep dependencies updated (Dependabot is configured for this repository)
- Review AWS IAM policies and S3 bucket policies before production use
