FROM python AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install honcho
RUN mkdir /app/staticfiles

FROM base AS service
WORKDIR /app
COPY . .
