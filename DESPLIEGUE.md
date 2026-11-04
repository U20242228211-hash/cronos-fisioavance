# Cómo poner Cronos en un servidor

Hay dos caminos. Cualquiera de los dos deja Cronos en un dominio de la institución, por ejemplo
`pqrsf.fisioavanceips.com`, sin tocar su página web en WordPress.

## Opción A · El hosting que ya tiene la IPS (cPanel)

Fisioavance usa un hosting compartido de Colombia Hosting con cPanel. Antes de empezar, confirme con el proveedor
que su plan tenga **«Setup Python App»** (Python 3.10 o más nuevo). Si no lo tiene, use la opción B.

1. **Subdominio.** En cPanel → *Dominios* → cree `pqrsf.fisioavanceips.com`.
2. **Base de datos.** En *Bases de datos MySQL* cree la base, un usuario y asígnele todos los privilegios.
3. **Código.** Suba la carpeta de Cronos (o clónela con *Git Version Control*) fuera de `public_html`, por
   ejemplo en `~/cronos`.
4. **Aplicación Python.** En *Setup Python App* → *Create Application*:
   - Python: la versión más nueva disponible.
   - Application root: `cronos`.
   - Application URL: `pqrsf.fisioavanceips.com`.
   - Application startup file: `passenger_wsgi.py` · Entry point: `application`.
5. **Librerías.** En la misma pantalla, «Run Pip Install» con `requirements.txt` (o desde la terminal del entorno
   virtual que muestra cPanel: `pip install -r requirements.txt`).
6. **Variables.** Cree el archivo `.env` (copie `.env.example`) con:
   ```
   DJANGO_SECRET_KEY=una-clave-larga-y-secreta
   DJANGO_DEBUG=0
   DJANGO_ALLOWED_HOSTS=pqrsf.fisioavanceips.com
   DJANGO_CSRF_TRUSTED_ORIGINS=https://pqrsf.fisioavanceips.com
   DATABASE_URL=mysql://USUARIO:CLAVE@localhost/BASE
   EMAIL_URL=smtp://pqrsf%40fisioavanceips.com:CLAVE@mail.fisioavanceips.com:465
   DEFAULT_FROM_EMAIL=Fisioavance IPS <pqrsf@fisioavanceips.com>
   ```
7. **Preparar.** En la terminal del entorno virtual:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py crear_institucion "Fisioavance IPS" --slug fisioavance --usuario cristhian --correo CORREO
   ```
   En **Institución** ponga `pqrsf.fisioavanceips.com` como *dominio propio*: así la raíz del subdominio abre
   directo el portal de Fisioavance.
8. **Certificado.** En *SSL/TLS Status* active el certificado gratuito para el subdominio.
9. **Alertas cada hora.** En *Cron Jobs*:
   ```
   0 * * * * cd ~/cronos && ~/virtualenv/cronos/3.13/bin/python manage.py revisar_vencimientos
   ```
   (la ruta exacta del Python la muestra *Setup Python App*).
10. **Enlace en la página.** En WordPress basta un botón «PQRSF» que lleve a `https://pqrsf.fisioavanceips.com`.

## Opción B · Un servidor propio (VPS) con Docker

Sirve si el hosting no acepta Python, o para ofrecer Cronos a varias instituciones desde un solo servidor.

```bash
git clone https://github.com/U20242228211-hash/cronos-fisioavance.git cronos && cd cronos
cp .env.example .env      # DJANGO_DEBUG=0, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS, EMAIL_URL
export POSTGRES_PASSWORD=una-clave-segura
docker compose up -d --build
docker compose exec web python manage.py crear_institucion "Fisioavance IPS" --slug fisioavance --usuario cristhian
```

Delante del contenedor va un proxy con HTTPS (Caddy o Nginx con Let's Encrypt). Para el dominio de la IPS, en la
zona DNS de su hosting se crea un registro **A** `pqrsf` → la IP del VPS, y en Cronos se pone ese dominio como
*dominio propio* de la institución. Cada institución nueva puede tener su propio dominio o entrar por
`https://servidor/su-identificador/`.

Las alertas se programan con el cron del servidor:
```
0 * * * * docker compose -f /ruta/cronos/docker-compose.yml exec -T web python manage.py revisar_vencimientos
```

## Antes de usarlo con pacientes reales

- Cambie todas las claves de prueba y cree los usuarios reales desde el panel.
- Cargue el **aviso de privacidad** definitivo de la institución y su política de tratamiento de datos (Ley 1581
  de 2012).
- Cargue las aseguradoras con las que trabaja y revise los servicios y profesionales.
- Imprima los carteles con QR desde el panel (*Carteles con QR*) y póngalos en recepción y en el buzón.
- Haga copias de seguridad de la base de datos (cPanel las hace a diario; en un VPS, prográmelas).
