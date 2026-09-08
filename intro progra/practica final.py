"""
total = 0
for n in range(2, 9):
    if n % 4 == 0:
        total += n
    elif n % 2 == 0:
        total += 2
print(total)

"""



"""

2 no es multiple de 4 pero se suman 2  porque entra en elif   entonces    0 + 2 = 2

3 no entra

4 entra en if asi que 4 + 2  = 6

5 no entra 

6 es multiplo de dos asi que se suman dos    6 + 2 = 8

7 no entra

8 entra asi que  8 + 8 = 16

la respuesta final es 16 porque fueron los resultados sumados que entraron en el if y en el elif


"""




"""

Ejercicio 2) Resolvé el siguiente problema

Consigna: Un gimnasio necesita gestionar los datos de sus socios. Los socios se clasifican por plan (Mensual, Trimestral, Anual) y tienen un estado (Activo, Vencido).

Estructura de datos: Crear una tupla para representar cada socio, con: DNI, nombre, plan, precio, estado.

Carga de datos: Crear una tupla que contenga estos datos:

("30111222", "Lucas Fernandez", "Mensual", 15000, "Activo")
("29888777", "Sofia Ramirez", "Anual", 120000, "Activo")
("31222333", "Diego Torres", "Trimestral", 40000, "Vencido")
("28555666", "Valentina Cruz", "Mensual", 15000, "Vencido")
("32444555", "Martin Sosa", "Anual", 120000, "Activo")

Menú de opciones:

a) Listado Total: Mostrar todos los socios.
b) Filtrar por Plan: Mostrar los socios de un plan específico ingresado por el usuario.
s) Salir del Programa.

Requisito: usar al menos una función.

Entrega: un archivo .py que contenga:

Respuesta del Ejercicio 1 como comentario, con la explicación.
Código del Ejercicio 2, funcionando.

"""


socios = ( 
("30111222", "Lucas Fernandez", "Mensual", 15000, "Activo"),
("29888777", "Sofia Ramirez", "Anual", 120000, "Activo"),
("31222333", "Diego Torres", "Trimestral", 40000, "Vencido"),
("28555666", "Valentina Cruz", "Mensual", 15000, "Vencido"),
("32444555", "Martin Sosa", "Anual", 120000, "Activo"),
)

def listado_socios (socios):
    for plan in socios:
        print (plan [0], plan [1], plan [2], plan [3], plan [4])




def filtrar_plan (socios, plan_buscado):
    for socio in socios:
        if socio [2].lower() == plan_buscado.lower():
            print (socio [0], socio [1], socio [2], socio [3], socio [4])

while True:
    print("a) todos los socios")

    print ("b) filtrar por plan")

    print ("c) salir del programa")

    opcion = input (" elija una opcion ")

    if opcion == "a":
        listado_socios (socios)

    elif opcion == "b":
        plan_buscado = input ("que plan quiere ver?")  
        filtrar_plan (socios, plan_buscado)
        

    elif opcion == "c":
        break
