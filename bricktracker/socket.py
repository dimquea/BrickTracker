import logging
from typing import Any, Final, Tuple

from flask import Flask, request
from flask_socketio import SocketIO

from .instructions import BrickInstructions
from .instructions_list import BrickInstructionsList
from .peeron_instructions import PeeronInstructions, PeeronPage
from .peeron_pdf import PeeronPDF
from .set import BrickSet
from .socket_decorator import authenticated_socket, catalog_socket
from .sql import close as sql_close

logger = logging.getLogger(__name__)

# Messages valid through the socket
# На сколько импорт уступает управление циклу gevent
#
# Пауза ненулевая намеренно: gevent.sleep(0) переключается только между
# готовыми greenlet-ами, а тот, которым gunicorn отмечается живым, ждёт
# таймера, и без полного оборота цикла он его не дождётся.
YIELD_SECONDS: Final[float] = 0.001

MESSAGES: Final[dict[str, str]] = {
    'COMPLETE': 'complete',
    'CONNECT': 'connect',
    'CREATE_LOT': 'create_lot',
    'CREATE_BULK_INDIVIDUAL_PARTS': 'create_bulk_individual_parts',
    'DISCONNECT': 'disconnect',
    'DOWNLOAD_INSTRUCTIONS': 'download_instructions',
    'DOWNLOAD_PEERON_PAGES': 'download_peeron_pages',
    'FAIL': 'fail',
    'IMPORT_MINIFIGURE': 'import_minifigure',
    'IMPORT_SET': 'import_set',
    'LOAD_MINIFIGURE': 'load_minifigure',
    'LOAD_PART': 'load_part',
    'LOAD_PART_COLORS': 'load_part_colors',
    'LOAD_PEERON_PAGES': 'load_peeron_pages',
    'LOAD_SET': 'load_set',
    'MINIFIGURE_LOADED': 'minifigure_loaded',
    'PART_COLORS_LOADED': 'part_colors_loaded',
    'PART_LOADED': 'part_loaded',
    'PROGRESS': 'progress',
    'SET_LOADED': 'set_loaded',
}


# Flask socket.io with our extra features
class BrickSocket(object):
    app: Flask
    socket: SocketIO
    threaded: bool

    # Progress
    progress_message: str
    progress_total: int
    progress_count: int

    def __init__(
        self,
        app: Flask,
        *args,
        threaded: bool = True,
        **kwargs
    ):
        # Save the app
        self.app = app

        # Progress
        self.progress_message = ''
        self.progress_count = 0
        self.progress_total = 0

        # Save the threaded flag
        self.threaded = threaded

        # Compute the namespace
        self.namespace = '/{namespace}'.format(
            namespace=app.config['SOCKET_NAMESPACE']
        )

        # Inject CORS if a domain is defined
        # Note: For reverse proxy deployments, leave BK_DOMAIN_NAME empty to allow all origins
        # When empty, Socket.IO defaults to permissive CORS which works with reverse proxies
        if app.config['DOMAIN_NAME'] != '':
            kwargs['cors_allowed_origins'] = app.config['DOMAIN_NAME']

        # Instantiate the socket
        self.socket = SocketIO(
            self.app,
            *args,
            **kwargs,
            path=app.config['SOCKET_PATH'],
            async_mode='gevent',
            # Enable detailed logging in debug mode for troubleshooting
            logger=app.config['DEBUG'],
            # Ping/pong settings for mobile network resilience
            ping_timeout=30,  # Wait 30s for pong response before disconnecting
            ping_interval=25,  # Send ping every 25s to keep connection alive
        )

        # Store the socket in the app config
        self.app.config['_SOCKET'] = self

        # Setup the socket
        @self.socket.on(MESSAGES['CONNECT'], namespace=self.namespace)
        def connect() -> None:
            self.connected()

        @self.socket.on(MESSAGES['DISCONNECT'], namespace=self.namespace)
        def disconnect(reason=None) -> None:
            self.disconnected()

        @self.socket.on('connect_error', namespace=self.namespace)
        def connect_error(data) -> None:
            logger.error(f'Socket CONNECT_ERROR: {data}')

        @self.socket.on_error(namespace=self.namespace)
        def error_handler(e) -> None:
            logger.error(f'Socket ERROR: {e}')
            try:
                user_agent = request.headers.get('User-Agent', 'unknown')
                remote_addr = request.remote_addr
                logger.error(f'Socket ERROR details: ip={remote_addr}, ua={user_agent[:80]}...')
            except Exception:
                pass

        @self.socket.on(MESSAGES['DOWNLOAD_INSTRUCTIONS'], namespace=self.namespace)  # noqa: E501
        @authenticated_socket(self)
        def download_instructions(data: dict[str, Any], /) -> None:
            instructions = BrickInstructions(
                '{name}.pdf'.format(name=data.get('alt', '')),
                socket=self
            )

            path = data.get('href', '').removeprefix('/instructions/')

            # Update the progress
            try:
                self.progress_total = int(data.get('total', 0))
                self.progress_count = int(data.get('current', 0))
            except Exception:
                pass

            instructions.download(path)

            BrickInstructionsList(force=True)

        @self.socket.on(MESSAGES['LOAD_PEERON_PAGES'], namespace=self.namespace)  # noqa: E501
        def load_peeron_pages(data: dict[str, Any], /) -> None:
            logger.debug('Socket: LOAD_PEERON_PAGES={data} (from: {fr})'.format(
                data=data, fr=request.remote_addr))

            try:
                set_number = data.get('set', '')
                if not set_number:
                    self.fail(message="Set number is required")
                    return

                # Create Peeron instructions instance with socket for progress reporting
                peeron = PeeronInstructions(set_number, socket=self)

                # Find pages (this will report progress for thumbnail caching)
                pages = peeron.find_pages()

                # Complete the operation (JavaScript will handle redirect)
                self.complete(message=f"Found {len(pages)} instruction pages on Peeron")

            except Exception as e:
                logger.error(f"Error in load_peeron_pages: {e}")
                self.fail(message=f"Error loading Peeron pages: {e}")

        @self.socket.on(MESSAGES['DOWNLOAD_PEERON_PAGES'], namespace=self.namespace)  # noqa: E501
        @authenticated_socket(self)
        def download_peeron_pages(data: dict[str, Any], /) -> None:
            logger.debug('Socket: DOWNLOAD_PEERON_PAGES={data} (from: {fr})'.format(
                data=data,
                fr=request.sid,  # type: ignore
            ))

            try:
                # Extract data from the request
                set_number = data.get('set', '')
                pages_data = data.get('pages', [])

                if not set_number:
                    raise ValueError("Set number is required")

                if not pages_data:
                    raise ValueError("No pages selected")

                # Parse set number
                if '-' in set_number:
                    parts = set_number.split('-', 1)
                    set_num = parts[0]
                    version_num = parts[1] if len(parts) > 1 else '1'
                else:
                    set_num = set_number
                    version_num = '1'

                # Convert page data to PeeronPage objects
                pages = []
                for page_data in pages_data:
                    page = PeeronPage(
                        page_number=page_data.get('page_number', ''),
                        original_image_url=page_data.get('original_image_url', ''),
                        cached_full_image_path=page_data.get('cached_full_image_path', ''),
                        cached_thumbnail_url='',  # Not needed for PDF generation
                        alt_text=page_data.get('alt_text', ''),
                        rotation=page_data.get('rotation', 0)
                    )
                    pages.append(page)

                # Create PDF generator and start download
                pdf_generator = PeeronPDF(set_num, version_num, pages, socket=self)
                pdf_generator.create_pdf()

                # Note: Cache cleanup is handled automatically by pdf_generator.create_pdf()

                # Refresh instructions list to include new PDF
                BrickInstructionsList(force=True)

            except Exception as e:
                logger.error(f"Error in download_peeron_pages: {e}")
                self.fail(message=f"Error downloading Peeron pages: {e}")

        @self.socket.on(MESSAGES['IMPORT_SET'], namespace=self.namespace)
        @catalog_socket(self)
        def import_set(data: dict[str, Any], /) -> None:
            logger.debug('Socket: IMPORT_SET={data} (from: {fr})'.format(
                data=data,
                fr=request.sid,  # type: ignore
            ))

            BrickSet().download(self, data)

        @self.socket.on(MESSAGES['LOAD_SET'], namespace=self.namespace)
        def load_set(data: dict[str, Any], /) -> None:
            logger.debug('Socket: LOAD_SET={data} (from: {fr})'.format(
                data=data,
                fr=request.sid,  # type: ignore
            ))

            BrickSet().load(self, data)

        @self.socket.on(MESSAGES['IMPORT_MINIFIGURE'], namespace=self.namespace)
        @catalog_socket(self)
        def import_minifigure(data: dict[str, Any], /) -> None:
            logger.debug('Socket: IMPORT_MINIFIGURE={data} (from: {fr})'.format(
                data=data,
                fr=request.sid,  # type: ignore
            ))

            from .individual_minifigure import IndividualMinifigure
            IndividualMinifigure().download(self, data)

        @self.socket.on(MESSAGES['LOAD_MINIFIGURE'], namespace=self.namespace)
        def load_minifigure(data: dict[str, Any], /) -> None:
            logger.debug('Socket: LOAD_MINIFIGURE={data} (from: {fr})'.format(
                data=data,
                fr=request.sid,  # type: ignore
            ))

            from .individual_minifigure import IndividualMinifigure
            IndividualMinifigure().load(self, data)

        @self.socket.on(MESSAGES['LOAD_PART'], namespace=self.namespace)
        def load_part(data: dict[str, Any], /) -> None:
            logger.debug('Socket: LOAD_PART={data} (from: {fr})'.format(
                data=data,
                fr=request.sid,  # type: ignore
            ))

            from .individual_part import IndividualPart
            IndividualPart().add(self, data)

        @self.socket.on(MESSAGES['LOAD_PART_COLORS'], namespace=self.namespace)
        def load_part_colors(data: dict[str, Any], /) -> None:
            logger.debug('Socket: LOAD_PART_COLORS={data} (from: {fr})'.format(
                data=data,
                fr=request.sid,  # type: ignore
            ))

            from .individual_part import IndividualPart
            IndividualPart().load_colors(self, data)

        @self.socket.on(MESSAGES['CREATE_LOT'], namespace=self.namespace)
        @catalog_socket(self)
        def create_lot(data: dict[str, Any], /) -> None:
            logger.debug('Socket: CREATE_LOT (from: {fr})'.format(
                fr=request.sid,  # type: ignore
            ))

            from .individual_part_lot import IndividualPartLot
            IndividualPartLot().create(self, data)

        @self.socket.on(MESSAGES['CREATE_BULK_INDIVIDUAL_PARTS'], namespace=self.namespace)
        @catalog_socket(self)
        def create_bulk_individual_parts(data: dict[str, Any], /) -> None:
            logger.debug('Socket: CREATE_BULK_INDIVIDUAL_PARTS (from: {fr})'.format(
                fr=request.sid,  # type: ignore
            ))

            from .individual_part import IndividualPart
            IndividualPart().create_bulk(self, data)

    # Update the progress auto-incrementing
    def auto_progress(
        self,
        /,
        *,
        message: str | None = None,
        increment_total=False,
    ) -> None:
        # Auto-increment
        self.progress_count += 1

        if increment_total:
            self.progress_total += 1

        self.progress(message=message)

    # Send a complete
    def complete(self, /, **data: Any) -> None:
        self.emit('COMPLETE', data)

        # Close any dangling connection
        sql_close()

    # Socket is connected
    def connected(self, /) -> Tuple[str, int]:
        # Get detailed connection info for debugging
        try:
            sid = request.sid  # type: ignore
            transport = request.environ.get('HTTP_UPGRADE', 'polling')
            user_agent = request.headers.get('User-Agent', 'unknown')
            remote_addr = request.remote_addr

            # Check if it's likely a mobile device
            is_mobile = any(x in user_agent.lower() for x in ['iphone', 'ipad', 'android', 'mobile'])

            logger.info(
                f'Socket CONNECTED: sid={sid}, transport={transport}, '
                f'ip={remote_addr}, mobile={is_mobile}, ua={user_agent[:80]}...'
            )
        except Exception as e:
            logger.warning(f'Socket connected but failed to get details: {e}')

        return '', 301

    # Socket is disconnected
    def disconnected(self, /) -> None:
        try:
            sid = request.sid  # type: ignore
            logger.info(f'Socket DISCONNECTED: sid={sid}')
        except Exception as e:
            logger.info(f'Socket disconnected (sid unavailable): {e}')

    # Emit a message through the socket
    def emit(self, name: str, *arg, all=False) -> None:
        # Emit to all sockets
        if all:
            to = None
        else:
            # Grab the request SID
            # This keeps message isolated between clients (and tabs!)
            try:
                to = request.sid  # type: ignore
            except Exception:
                logger.debug('Unable to load request.sid')
                to = None

            logger.debug('Socket: {name}={args} (to: {to})'.format(
                name=name,
                args=arg,
                to=to,
            ))

        self.socket.emit(
            MESSAGES[name],
            *arg,
            namespace=self.namespace,
            to=to,
        )

        # Уступаем управление циклу gevent
        #
        # Импорт набора почти не делает того, на чём gevent переключает
        # задачи: разбор каталога и работа с SQLite — это процессор и
        # сишные вызовы, а картинки, если они уже в кэше, не качаются.
        # Получается один длинный кусок кода без единой точки переключения,
        # и greenlet, которым gunicorn отмечается живым, просто не
        # получает управления. Через timeout секунд арбитр решает, что
        # воркер завис, и убивает его — на 10188-1 с его 27 фигурками это
        # случалось на 97 процентах.
        #
        # Заодно накопленные сообщения о ходе дела наконец уходят клиенту
        # по мере работы, а не пачкой в конце.
        self.socket.sleep(YIELD_SECONDS)

    # Send a failed
    def fail(self, /, **data: Any) -> None:
        self.emit('FAIL', data)

        # Close any dangling connection
        sql_close()

    # Update the progress
    def progress(self, /, *, message: str | None = None) -> None:
        # Save the las message
        if message is not None:
            self.progress_message = message

        # Prepare data
        data: dict[str, Any] = {
            'message': self.progress_message,
            'count': self.progress_count,
            'total': self.progress_total,
        }

        self.emit('PROGRESS', data)

    # Update the progress total only
    def update_total(self, total: int, /, *, add: bool = False) -> None:
        if add:
            self.progress_total += total
        else:
            self.progress_total = total

    # Update the total
    def total_progress(self, total: int, /, *, add: bool = False) -> None:
        self.update_total(total, add=add)

        self.progress()
