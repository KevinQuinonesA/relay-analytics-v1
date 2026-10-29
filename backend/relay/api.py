from fastapi import FastAPI

app = FastAPI(title="Relay weekly normality")


def get_conn():
    raise NotImplementedError
