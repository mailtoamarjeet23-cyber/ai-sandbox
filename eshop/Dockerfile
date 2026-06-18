FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /app

# --depth=1 skips full history — faster clone
RUN git clone --depth=1 https://github.com/NimblePros/eShopOnWeb.git .

RUN dotnet restore
RUN dotnet build --configuration Release --no-restore

# Keep SDK image (not aspnet runtime) so we can run dotnet-ef and dotnet test at container start
FROM mcr.microsoft.com/dotnet/sdk:8.0
WORKDIR /app

COPY --from=build /app .

RUN dotnet tool install --global dotnet-ef
ENV PATH="$PATH:/root/.dotnet/tools"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
