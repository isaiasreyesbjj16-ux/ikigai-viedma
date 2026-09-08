"""
Examen de práctica — Introducción a la Programación
Ejercicio 1) Salida de programa
python
total = 0
for n in range(1, 8):
    if n % 2 == 0:
        total += n
    else:
        total += 1
print(total)

A. 17 B. 16 C. 20 D. 14

Armá tu tabla completa (n, condición, qué se suma, total antes/después) y decime tu respuesta con la explicación.

Ejercicio 2) Resolvé el siguiente problema

Consigna: Una veterinaria necesita gestionar los turnos de sus pacientes (mascotas). Los turnos se clasifican por tipo de atención (Consulta, Vacunación, Cirugía) y tienen un estado (Confirmado, Cancelado).

Estructura de datos: Crear una tupla para representar cada turno, con: codigo_turno, mascota, tipo_atencion, costo, estado.

Carga de datos: Crear una tupla que contenga estos datos:

("TUR-01", "Rocky", "Consulta", 5000, "Confirmado")
("TUR-02", "Michi", "Vacunacion", 3500, "Confirmado")
("TUR-03", "Toby", "Cirugia", 45000, "Cancelado")
("TUR-04", "Luna", "Consulta", 5000, "Cancelado")
("TUR-05", "Simba", "Vacunacion", 3500, "Confirmado")

Menú de opciones:

a) Listado Total: Mostrar todos los turnos.
b) Filtrar por Tipo de Atención: Mostrar los turnos de un tipo específico ingresado por el usuario.
s) Salir del Programa.

Requisito: usar al menos una función.

Entrega: un archivo .py que contenga:

Respuesta del Ejercicio 1 como comentario, con la explicación.
Código del Ejercicio 2, funcionando.

"""


"""
1 no entra pero se suma 0 + 1 = 1
2 si entra 2 + 1 = 3
3 no entra asi que suma 1 + 3 = 4
4 entra asi que 4 + 4 = 8
5 no entra asi que suma 1. 1 + 8 = 9
6 entra asi que se suma 6 + 9 = 15
7 no entra asi que se suma 1 = 16


"""


Datos_Mascotas = (
("TUR-01", "Rocky", "Consulta", 5000, "Confirmado"),
("TUR-02", "Michi", "Vacunacion", 3500, "Confirmado"),
("TUR-03", "Toby", "Cirugia", 45000, "Cancelado"),
("TUR-04", "Luna", "Consulta", 5000, "Cancelado"),
("TUR-05", "Simba", "Vacunacion", 3500, "Confirmado"),

)


def datos (Datos_Mascotas):
    for mascotas in Datos_Mascotas:
        print (mascotas [0], mascotas [1], mascotas [2], mascotas [3], mascotas[4])


def turno (Datos_Mascotas, atencion):
    for turnos in Datos_Mascotas:
        if turnos[2].lower() == atencion.lower():
            print (turnos [0], turnos [1], turnos [2], turnos [3], turnos[4])


while True:
    print("a) Listado Total: Mostrar todos los turnos.")
    print ("b) Filtrar por Tipo de Atención: Mostrar los turnos de un tipo específico ingresado por el usuario.")
    print ("s) Salir del Programa.")

    tipo_turno = input (" Seleccione una opcion ")

    if tipo_turno == "a":
        datos(Datos_Mascotas)

    elif tipo_turno == "b":
        atencion = input (" Diga su atencion: ")
        turno (Datos_Mascotas, atencion)

    elif tipo_turno == "s":
        break
