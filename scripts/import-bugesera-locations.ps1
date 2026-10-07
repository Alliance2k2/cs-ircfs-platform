$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $root ".env"
$envText = Get-Content $envFile -Raw
$dbUrl = [regex]::Match($envText, 'DATABASE_URL=postgresql\+psycopg://([^:]+):([^@]+)@([^:]+):(\d+)/([^\r\n]+)').Groups
if (-not $dbUrl[0].Success) { throw "Could not read DATABASE_URL from .env" }
$user,$password,$dbHost,$port,$database = $dbUrl[1].Value,$dbUrl[2].Value,$dbUrl[3].Value,$dbUrl[4].Value,$dbUrl[5].Value
$ogr = "C:\Program Files\QGIS 3.44.14\bin\ogr2ogr.exe"
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (-not (Test-Path $ogr)) { throw "ogr2ogr was not found at $ogr" }
if (-not (Test-Path $psql)) { throw "psql was not found at $psql" }
$pg = "PG:host=$dbHost port=$port dbname=$database user=$user password=$password"
$data = Join-Path $root "data"
$importSectors = "import_sectors"
$importCells = "import_cells"
& $ogr -f PostgreSQL $pg (Join-Path $data "bugesera_sectors.gpkg") -nln $importSectors -nlt MULTIPOLYGON -lco GEOMETRY_NAME=geom -lco FID=fid -overwrite
& $ogr -f PostgreSQL $pg (Join-Path $data "bugesera_cells.gpkg") -nln $importCells -nlt MULTIPOLYGON -lco GEOMETRY_NAME=geom -lco FID=fid -overwrite
$env:PGPASSWORD = $password
$sql = @"
INSERT INTO sectors (name, latitude, longitude, boundary)
SELECT DISTINCT sector, ST_Y(ST_PointOnSurface(geom)), ST_X(ST_PointOnSurface(geom)), ST_Multi(ST_Force2D(geom))
FROM $importSectors WHERE sector IS NOT NULL
ON CONFLICT (name) DO UPDATE SET boundary=EXCLUDED.boundary, latitude=EXCLUDED.latitude, longitude=EXCLUDED.longitude;
INSERT INTO cells (name, sector_id, latitude, longitude, boundary)
SELECT i.cell, s.id, ST_Y(ST_PointOnSurface(i.geom)), ST_X(ST_PointOnSurface(i.geom)), ST_Multi(ST_Force2D(i.geom))
FROM $importCells i JOIN sectors s ON s.name=i.sector
WHERE i.cell IS NOT NULL
ON CONFLICT DO NOTHING;
DROP TABLE IF EXISTS $importSectors;
DROP TABLE IF EXISTS $importCells;
SELECT 'sectors' AS table_name, count(*) FROM sectors;
SELECT 'cells' AS table_name, count(*) FROM cells;
"@
$sql | & $psql -h $dbHost -p $port -U $user -d $database -v ON_ERROR_STOP=1
Write-Host "Bugesera sectors and cells imported successfully." -ForegroundColor Green
