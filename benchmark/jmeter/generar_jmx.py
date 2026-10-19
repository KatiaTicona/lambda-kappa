"""Genera los planes JMeter rest.jmx y graphql.jmx (mismo escenario que locustfile.py)."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent

ARGS_VACIOS = ('<elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" '
               'testclass="Arguments" testname="User Defined Variables" enabled="true">'
               '<collectionProp name="Arguments.arguments"/></elementProp>')

PLAN = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="@@NOMBRE@@" enabled="true">
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments" guiclass="ArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Usuarios" enabled="true">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControlPanel" testclass="LoopController" testname="Loop Controller" enabled="true">
          <boolProp name="LoopController.continue_forever">false</boolProp>
          <intProp name="LoopController.loops">-1</intProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">${__P(users,10)}</stringProp>
        <stringProp name="ThreadGroup.ramp_time">${__P(ramp,1)}</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">${__P(duration,40)}</stringProp>
        <stringProp name="ThreadGroup.delay"></stringProp>
        <boolProp name="ThreadGroup.same_user_on_next_iteration">true</boolProp>
      </ThreadGroup>
      <hashTree>
        <ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults" enabled="true">
          @@ARGS@@
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
          <stringProp name="HTTPSampler.port">@@PUERTO@@</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
        </ConfigTestElement>
        <hashTree/>
        <TransactionController guiclass="TransactionControllerGui" testclass="TransactionController" testname="dashboard" enabled="true">
          <boolProp name="TransactionController.includeTimers">false</boolProp>
          <boolProp name="TransactionController.parent">true</boolProp>
        </TransactionController>
        <hashTree>
@@SAMPLERS@@
        </hashTree>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""


def get(nombre, ruta):
    return f"""          <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="{nombre}" enabled="true">
            {ARGS_VACIOS}
            <stringProp name="HTTPSampler.path">{escape(ruta)}</stringProp>
            <stringProp name="HTTPSampler.method">GET</stringProp>
            <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
            <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
            <boolProp name="HTTPSampler.DO_MULTIPART_POST">false</boolProp>
          </HTTPSamplerProxy>
          <hashTree/>
"""


def post_graphql():
    consulta = ('{ resumen(fuente: "${__P(fuente,kappa)}") { eventType eventos monto } '
                'serie(fuente: "${__P(fuente,kappa)}", tipo: "pago", minutos: ${__P(minutos,60)}) '
                '{ minute eventos } }')
    cuerpo = escape(json.dumps({"query": consulta}))
    return f"""          <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="graphql" enabled="true">
            <boolProp name="HTTPSampler.postBodyRaw">true</boolProp>
            <elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">
              <collectionProp name="Arguments.arguments">
                <elementProp name="" elementType="HTTPArgument">
                  <boolProp name="HTTPArgument.always_encode">false</boolProp>
                  <stringProp name="Argument.value">{cuerpo}</stringProp>
                  <stringProp name="Argument.metadata">=</stringProp>
                </elementProp>
              </collectionProp>
            </elementProp>
            <stringProp name="HTTPSampler.path">/graphql</stringProp>
            <stringProp name="HTTPSampler.method">POST</stringProp>
            <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
            <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
            <boolProp name="HTTPSampler.DO_MULTIPART_POST">false</boolProp>
          </HTTPSamplerProxy>
          <hashTree>
            <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager" testname="Content-Type" enabled="true">
              <collectionProp name="HeaderManager.headers">
                <elementProp name="" elementType="Header">
                  <stringProp name="Header.name">Content-Type</stringProp>
                  <stringProp name="Header.value">application/json</stringProp>
                </elementProp>
              </collectionProp>
            </HeaderManager>
            <hashTree/>
            <ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="sin errores GraphQL" enabled="true">
              <collectionProp name="Asserion.test_strings">
                <stringProp name="1">"errors"</stringProp>
              </collectionProp>
              <stringProp name="Assertion.custom_message"></stringProp>
              <stringProp name="Assertion.test_field">Assertion.response_data</stringProp>
              <boolProp name="Assertion.assume_success">false</boolProp>
              <intProp name="Assertion.test_type">6</intProp>
            </ResponseAssertion>
            <hashTree/>
          </hashTree>
"""


def escribir(archivo, nombre, puerto, samplers):
    xml = (PLAN.replace("@@NOMBRE@@", nombre).replace("@@PUERTO@@", str(puerto))
           .replace("@@ARGS@@", ARGS_VACIOS).replace("@@SAMPLERS@@", samplers))
    (OUT / archivo).write_text(xml, encoding="utf-8")


def main():
    rest = (get("resumen", "/resumen?fuente=${__P(fuente,kappa)}")
            + get("serie", "/serie?fuente=${__P(fuente,kappa)}&tipo=pago&minutos=${__P(minutos,60)}"))
    escribir("rest.jmx", "Dashboard REST", 8000, rest)
    escribir("graphql.jmx", "Dashboard GraphQL", 8001, post_graphql())
    print("Generados rest.jmx y graphql.jmx en", OUT)


if __name__ == "__main__":
    main()