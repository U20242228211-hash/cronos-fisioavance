import re

from django import forms

from instituciones.models import Aseguradora, Profesional, Servicio
from pqrsf.models import PQRSF, Tipo

AYUDA_TIPO = {
    Tipo.PETICION: "Pedir algo: una cita, un documento, información.",
    Tipo.QUEJA: "Algo de la atención o de una persona no le gustó.",
    Tipo.RECLAMO: "No le prestaron un servicio o se lo prestaron mal.",
    Tipo.SUGERENCIA: "Una idea para que mejoremos.",
    Tipo.FELICITACION: "Algo o alguien lo hizo sentir bien atendido.",
}
ICONO_TIPO = {
    Tipo.PETICION: "help",
    Tipo.QUEJA: "sentiment_dissatisfied",
    Tipo.RECLAMO: "report",
    Tipo.SUGERENCIA: "lightbulb",
    Tipo.FELICITACION: "favorite",
}


class PQRSFPublicaForm(forms.ModelForm):
    class Meta:
        model = PQRSF
        fields = [
            "tipo", "servicio", "profesional", "descripcion", "adjunto", "anonima", "tipo_documento",
            "numero_documento", "nombres", "apellidos", "telefono", "correo", "sexo", "fecha_nacimiento",
            "municipio", "vinculacion", "aseguradora", "condicion_especial", "es_acudiente", "nombre_paciente",
            "medio_respuesta", "autoriza_datos",
        ]
        widgets = {
            "tipo": forms.RadioSelect,
            "descripcion": forms.Textarea(attrs={"rows": 5, "placeholder": "Cuéntenos qué pasó, cuándo y con quién."}),
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "medio_respuesta": forms.RadioSelect,
            "vinculacion": forms.RadioSelect,
            "telefono": forms.TextInput(attrs={"inputmode": "tel", "placeholder": "3001234567"}),
            "correo": forms.EmailInput(attrs={"placeholder": "nombre@correo.com"}),
            "numero_documento": forms.TextInput(attrs={"inputmode": "numeric"}),
        }
        labels = {
            "tipo": "¿Qué quiere hacer?",
            "servicio": "¿En qué servicio?",
            "profesional": "¿Quién lo atendió? (opcional)",
            "descripcion": "Cuéntenos",
            "adjunto": "Foto o documento (opcional)",
            "anonima": "Prefiero no dar mis datos",
            "es_acudiente": "La presento en nombre de un paciente (soy acudiente)",
            "autoriza_datos": "Autorizo el tratamiento de mis datos personales",
            "medio_respuesta": "¿Por dónde quiere la respuesta?",
            "vinculacion": "¿Cómo lo atendieron?",
        }

    def __init__(self, *args, institucion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institucion = institucion
        self.fields["servicio"].queryset = Servicio.objects.filter(institucion=institucion, activo=True)
        self.fields["servicio"].empty_label = "Elija el servicio"
        self.fields["profesional"].queryset = Profesional.objects.filter(institucion=institucion, activo=True)
        self.fields["profesional"].empty_label = "No sé o prefiero no decir"
        self.fields["aseguradora"].queryset = Aseguradora.objects.filter(institucion=institucion, activa=True)
        self.fields["aseguradora"].empty_label = "Elija la aseguradora"
        self.fields["tipo"].choices = list(Tipo.choices)
        self.fields["medio_respuesta"].choices = [
            (PQRSF.MedioRespuesta.WHATSAPP, "WhatsApp"),
            (PQRSF.MedioRespuesta.CORREO, "Correo electrónico"),
        ]
        self.fields["medio_respuesta"].required = False
        self.fields["vinculacion"].choices = list(PQRSF.Vinculacion.choices)
        self.fields["vinculacion"].required = False
        self.fields["tipo_documento"].choices = [("", "Tipo")] + list(PQRSF.TipoDocumento.choices)
        self.fields["sexo"].choices = [("", "Elija")] + list(PQRSF.Sexo.choices)
        self.fields["servicio"].required = True
        for nombre in ("nombres", "apellidos", "numero_documento", "telefono", "correo", "municipio"):
            self.fields[nombre].widget.attrs.setdefault("autocomplete", "off")

    def opciones_tipo(self):
        valor = self["tipo"].value()
        return [
            {"valor": v, "texto": t, "ayuda": AYUDA_TIPO[v], "icono": ICONO_TIPO[v], "elegido": valor == v}
            for v, t in Tipo.choices
        ]

    def clean_telefono(self):
        telefono = re.sub(r"\D", "", self.cleaned_data.get("telefono") or "")
        if telefono and len(telefono) not in (10, 12):
            raise forms.ValidationError("Escriba el celular de 10 dígitos, por ejemplo 3001234567.")
        return telefono

    def clean(self):
        datos = super().clean()
        if datos.get("anonima"):
            if datos.get("tipo") in (Tipo.PETICION,):
                self.add_error("anonima", "Una petición necesita sus datos para poder responderle.")
            datos["medio_respuesta"] = PQRSF.MedioRespuesta.AVISO
            return datos
        obligatorios = {
            "tipo_documento": "Elija el tipo de documento.",
            "numero_documento": "Escriba su número de documento.",
            "nombres": "Escriba su nombre.",
            "apellidos": "Escriba sus apellidos.",
        }
        for campo, mensaje in obligatorios.items():
            if not datos.get(campo):
                self.add_error(campo, mensaje)
        medio = datos.get("medio_respuesta")
        if not medio:
            self.add_error("medio_respuesta", "Elija por dónde quiere la respuesta.")
        elif medio == PQRSF.MedioRespuesta.WHATSAPP and not datos.get("telefono"):
            self.add_error("telefono", "Para responderle por WhatsApp necesitamos su celular.")
        elif medio == PQRSF.MedioRespuesta.CORREO and not datos.get("correo"):
            self.add_error("correo", "Para responderle por correo necesitamos su correo.")
        if datos.get("es_acudiente") and not datos.get("nombre_paciente"):
            self.add_error("nombre_paciente", "Escriba el nombre del paciente.")
        if datos.get("vinculacion") == PQRSF.Vinculacion.ASEGURADORA and not datos.get("aseguradora"):
            self.add_error("aseguradora", "Elija la aseguradora.")
        if not datos.get("autoriza_datos"):
            self.add_error("autoriza_datos", "Para recibir su PQRSF con sus datos necesitamos su autorización.")
        return datos


class ConsultaForm(forms.Form):
    radicado = forms.CharField(label="Número de radicado", widget=forms.TextInput(attrs={"placeholder": "FIS-2026-00012"}))
    documento = forms.CharField(
        label="Su número de documento o el código de consulta",
        help_text="Si la puso sin sus datos, use el código que le dimos al radicar.",
    )
