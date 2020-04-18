## Opinionated Serverless Flask

Comes with a lot of useful stuff ready to go.

Designed for serverless API development with PostgreSQL.

## Features

- [Flask Smorest](https://pypi.org/project/flask-smorest/)
  - OpenAPI
  - Swagger UI
  - Redoc
- [Pytest using database subtransactions](https://pypi.org/project/pytest-flask-sqlalchemy/) for test isolation
- [Pytest-FactoryBoy](https://pytest-factoryboy.readthedocs.io/en/latest/#model-fixture) for generating sample data for seeding DB and tests.
- Flake8 for linting
- [Mypy](http://mypy-lang.org/) for type-checking
- [Black](https://black.readthedocs.io/en/stable/) for formatting
- AWS Lambda integration
  - [Serverless AWS](https://serverless.com/framework/docs/providers/aws/)
  - [AWS Aurora Serverless Postgres](https://aws.amazon.com/rds/aurora/serverless/) for on-demand Postgresql DB with a [data-api query driver](https://github.com/chanzuckerberg/sqlalchemy-aurora-data-api#motivation) (optional).
  - Load Flask config from AWS Secrets Manager
- [Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/) for DB migrations with alembic and Flask CLI
- [Poetry](https://python-poetry.org/docs/) for dependency management

## Quickstart:

### Prerequisites:

```
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python  # poetry
npm i -g serverless
```

### Create Project:

```
npx sls install --url https://github.com/jetbridge/sls-flask --name myapp
cd myapp
make init  # install dependencies and initialize project
```

### Python Virtual Environment:

```
poetry shell  # activate python virtual environment
poetry install  # install dependencies
```

### Run Dev Server:

```
flask  # CLI commands
make run  # run flask dev server
sls wsgi serve  # run flask dev server under serverless
```


### Database:
Using Postgresql.
```
createdb TEMPLATE
flask db upgrade  # run migrations
flask seed  # populate with sample data
flask db migrate  # generate new migration
flask db  # more migration commands
```

### Deploy:
```
make deploy-dev   # deploy to AWS and run migrations
make deploy-prd  # deploy to AWS and run migrations
```

### API Documentation:

Once your flask dev server is running:

- [OpenAPI JSON](http://localhost:5000/api/openapi.json) (http://localhost:5000/api/openapi.json)
- [Swagger UI](http://localhost:5000/api/swagger) (http://localhost:5000/api/swagger)
- [ReDoc](http://localhost:5000/api/doc) (http://localhost:5000/api/doc)

### Database Driver
There are two options for database access: [Aurora Data API](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html) or psycopg2/libpq.

#### Aurora Data API
Allows the application to query the database using AWS API calls. Does not require lambdas to be in a VPC, reducing the need for NAT gateways reducing cost and complexity. Has limitations and is somewhat beta.

#### Psycopg2
Standard Python PostgreSQL database driver. More powerful and efficient but requires enabling lambda VPC networking.

##### To Enable:
* Uncomment VPC `subnetIds` config in `serverless.yml`
* Uncomment `- ${file(cloudformation/vpc/lambda.yml)}` resource inclusion in `serverless.yml`
