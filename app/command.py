from flask import Flask
from app import app

@app.cli.command()
def initdb():
    click.echo('TODO: run the SQL scripts to initialize the database.')

@app.cli.command()
def migratedb():
    pass
