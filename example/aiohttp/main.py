import asyncio
import aiohttp_jinja2
import jinja2
import aiopg.sa
from sqlalchemy.engine.url import URL
from aiohttp import web

from vision_tile_query import VisionBaseTileProcessor, AsyncTableManager

DNS = str(URL(
    database='vision_db',
    host='localhost',
    username='postgres',
    drivername='postgres',
))


async def init_pg(app):
    app['db'] = await aiopg.sa.create_engine(DNS)
    app['table_manager'] = AsyncTableManager(app['db'])


async def close_pg_connection(app):
    app['db'].close()
    await app['db'].wait_closed()


async def get_tile(request):
    params = dict(request.match_info)

    tile = {'x': int(params.get('x')),
            'y': int(params.get('y')),
            'z': int(params.get('z'))}

    # Define model
    model = await app['table_manager'].get_table_model(
        params.get('table'), 'public')

    tile_query = VisionBaseTileProcessor().get_tile(
        tile, model=model.__table__)

    async with app['db'].acquire() as conn:
        data = await conn.scalar(tile_query)

    response = web.Response(
            body=bytes(data),
            headers={
                'Content-Type': "application/x-protobuf",
            }
        )
    return response


@aiohttp_jinja2.template('main.html')
async def handle(request):
    return {'KEY': 'YOUR MAPBOX TOKEN'}


loop = asyncio.get_event_loop()
app = web.Application(loop=loop)
app.add_routes([web.get("/", handle),
                web.get("/tile/{table}/{z}/{x}/{y}.pbf", get_tile)
                ])
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))

app.update(name='vision-tile-query')

# signal on app start
app.on_startup.append(init_pg)
# signal on app end
app.on_cleanup.append(close_pg_connection)

web.run_app(app)
