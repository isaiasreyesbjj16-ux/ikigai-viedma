"""

Examen de práctica — Introducción a la Programación
Ejercicio 1) Salida de programa
python
total = 0
for n in range(1, 10):
    if n % 5 == 0:
        total += n
    elif n % 2 != 0:
        total += 3
print(total)

A. 25 B. 30 C. 27 D. 22

Armá tu tabla (n, condición, qué se suma, total antes/después) y decime qué opción elegís y por qué.

Ejercicio 2) Resolvé el siguiente problema

Consigna: Un restaurante necesita gestionar los pedidos de sus clientes. Los pedidos se clasifican por tipo (Delivery, Take Away, Salón) y tienen un estado (Pendiente, Entregado).

Estructura de datos: Crear una tupla para representar cada pedido, con: numero_pedido, cliente, tipo, monto, estado.

Carga de datos: Crear una tupla que contenga estos datos:

("PED-01", "Rocio Alvarez", "Delivery", 8500, "Pendiente")
("PED-02", "Nicolas Vega", "Salon", 6200, "Entregado")
("PED-03", "Camila Ortiz", "Take Away", 4300, "Entregado")
("PED-04", "Franco Molina", "Delivery", 9100, "Pendiente")
("PED-05", "Julieta Paz", "Salon", 7800, "Pendiente")

Menú de opciones:

a) Listado Total: Mostrar todos los pedidos.
b) Filtrar por Tipo: Mostrar los pedidos de un tipo específico ingresado por el usuario.
s) Salir del Programa.

Requisito: usar al menos una función.

Entrega: un archivo .py que contenga:

Respuesta del Ejercicio 1 como comentario, con la explicación.
Código del Ejercicio 2, funcionando.

Armalo entero (datos, las dos funciones, y el menú con while True) y mandame el archivo completo cuando lo tengas. Si te trabás en algún punto puntual, decime exactamente dónde, y ahí sí te voy guiando de nuevo en esa parte específica.

"""


"""
1 entra en el elif  3 + 0 = 1

2 no entra porque dice que tiene que ser distinto a 0

3 entra porque el resto es uno   entonces seria 3 + 3 = 6

4 no porque el resto es 0

5 entra. asi que seria 6+  5 = 11

6 entra porque el resto es distinto a 0 entonces

7 entra porque el resto 1  3 + 11 = 14 

8 no entra

9 entra 14 + 3 = 17

10 entra 17 + 10 = 27

"""






pedidos_clientes = (
     
("PED-01", "Rocio Alvarez", "Delivery", 8500, "Pendiente"),
("PED-02", "Nicolas Vega", "Salon", 6200, "Entregado"),
("PED-03", "Camila Ortiz", "Take Away", 4300, "Entregado"),
("PED-04", "Franco Molina", "Delivery", 9100, "Pendiente"),
("PED-05", "Julieta Paz", "Salon", 7800, "Pendiente"),


)


def datos_clientes (pedidos_clientes):
    for datos in pedidos_clientes:
            print(datos[0], datos[1], datos[2], datos[3], datos[4])



def detalle_pedido (pedidos_clientes, detalles_pedidos):

    for datos2 in pedidos_clientes:
        if datos2 [2].lower() == detalles_pedidos.lower():
             print  (datos2[0], datos2[1], datos2[2], datos2[3], datos2[4])

while True:
    print ("a) todos los pedidos")
    print ("b) tipo de pedido")
    print ("c) salir")

    datos= input (" seleccione una opcion ")

    if datos == "a":
        
        datos_clientes (pedidos_clientes)

    elif datos == "b":
        detalles_pedidos = input(" selecciones un detalle de pedido ")
        detalle_pedido (pedidos_clientes, detalles_pedidos)

    elif datos == "c":
        break
        

