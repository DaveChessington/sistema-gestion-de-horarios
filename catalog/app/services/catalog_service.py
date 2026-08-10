from catalog.app.extensions import db
from catalog.app.models.plantel import Plantel
from catalog.app.models.salon import Salon
from catalog.app.models.equipo import Equipo
from catalog.app.models.programa import Programa

# Excepciones personalizadas para un manejo de errores limpio
class EntityNotFoundException(Exception):
    """Excepción lanzada cuando una entidad no existe o está desactivada."""
    pass

class DuplicateEntityException(Exception):
    """Excepción lanzada cuando hay un conflicto por duplicidad de datos (ej. número de inventario)."""
    pass

class InvalidDataException(Exception):
    """Excepción lanzada cuando la data provista viola reglas de negocio (ej. capacidad <= 0 o asociaciones inválidas)."""
    pass


class CampusService:
    @staticmethod
    def create_plantel(nombre, direccion=None):
        if not nombre or not nombre.strip():
            raise InvalidDataException("El nombre del plantel es obligatorio y no puede estar vacío.")
        
        plantel = Plantel(nombre=nombre.strip(), direccion=direccion)
        db.session.add(plantel)
        db.session.commit()
        return plantel

    @staticmethod
    def get_plantel_by_id(plantel_id, active_only=True):
        query = Plantel.query.filter_by(id=plantel_id)
        if active_only:
            query = query.filter_by(activo=True)
        plantel = query.first()
        if not plantel:
            raise EntityNotFoundException(f"El plantel con ID {plantel_id} no existe o está inactivo.")
        return plantel

    @staticmethod
    def list_planteles(active_only=True):
        query = Plantel.query
        if active_only:
            query = query.filter_by(activo=True)
        return query.all()

    @staticmethod
    def update_plantel(plantel_id, nombre, direccion=None):
        plantel = CampusService.get_plantel_by_id(plantel_id, active_only=True)
        if not nombre or not nombre.strip():
            raise InvalidDataException("El nombre del plantel no puede estar vacío.")
        
        plantel.nombre = nombre.strip()
        plantel.direccion = direccion
        db.session.commit()
        return plantel

    @staticmethod
    def delete_plantel(plantel_id):
        plantel = CampusService.get_plantel_by_id(plantel_id, active_only=True)
        plantel.activo = False
        
        # Opcional: Desactivación en cascada lógica de todos sus salones
        for salon in plantel.salones:
            if salon.activo:
                salon.activo = False
                # Y de los equipos del salón
                for equipo in salon.equipos:
                    if equipo.activo:
                        equipo.activo = False
                        
        db.session.commit()
        return {"message": f"Plantel {plantel_id} y sus recursos dependientes desactivados lógicamente."}

    @staticmethod
    def create_salon(numero, descripcion, capacidad, id_plantel):
        # CA-04 (Caso Límite): Validar capacidad menor o igual a cero
        if capacidad is None or capacidad <= 0:
            raise InvalidDataException("La capacidad del salón debe ser mayor a cero.")
        
        if not numero or not str(numero).strip():
            raise InvalidDataException("El número de salón es obligatorio.")
        
        # Validar existencia del plantel
        CampusService.get_plantel_by_id(id_plantel, active_only=True)

        salon = Salon(
            numero=str(numero).strip(),
            descripcion=descripcion,
            capacidad=capacidad,
            id_plantel=id_plantel
        )
        db.session.add(salon)
        db.session.commit()
        return salon

    @staticmethod
    def get_salon_by_id(id_salon, active_only=True):
        query = Salon.query.filter_by(id_salon=id_salon)
        if active_only:
            query = query.filter_by(activo=True)
        salon = query.first()
        if not salon:
            raise EntityNotFoundException(f"El salón con ID {id_salon} no existe o está inactivo.")
        return salon

    @staticmethod
    def list_salones(active_only=True, id_plantel=None, software_id=None):
        query = Salon.query
        if active_only:
            # Filtrar salones activos de planteles activos
            query = query.filter_by(activo=True).join(Plantel).filter(Plantel.activo == True)
        
        if id_plantel:
            query = query.filter(Salon.id_plantel == id_plantel)
            
        if software_id:
            # Filtrar salones que tienen equipos con un software específico instalado
            query = query.join(Equipo).join(Equipo.programas).filter(
                Programa.id_programa == software_id,
                Programa.activo == True,
                Equipo.activo == True
            )
            
        return query.all()

    @staticmethod
    def update_salon(id_salon, numero, descripcion, capacidad, id_plantel):
        salon = CampusService.get_salon_by_id(id_salon, active_only=True)
        
        if capacidad is None or capacidad <= 0:
            raise InvalidDataException("La capacidad del salón debe ser mayor a cero.")
        
        if not numero or not str(numero).strip():
            raise InvalidDataException("El número de salón no puede estar vacío.")
            
        CampusService.get_plantel_by_id(id_plantel, active_only=True)

        salon.numero = str(numero).strip()
        salon.descripcion = descripcion
        salon.capacidad = capacidad
        salon.id_plantel = id_plantel
        db.session.commit()
        return salon

    @staticmethod
    def delete_salon(id_salon):
        salon = CampusService.get_salon_by_id(id_salon, active_only=True)
        salon.activo = False
        
        # Desactivación en cascada lógica de los equipos del salón
        for equipo in salon.equipos:
            if equipo.activo:
                equipo.activo = False
                
        db.session.commit()
        return {"message": f"Salón {id_salon} y sus equipos asociados desactivados lógicamente."}


class EquipmentService:
    @staticmethod
    def create_equipment(numero, descripcion, id_salon=None):
        if not numero or not str(numero).strip():
            raise InvalidDataException("El número de inventario del equipo es obligatorio.")
        
        numero_clean = str(numero).strip()
        
        # Validar duplicidad de número de inventario
        existente = Equipo.query.filter_by(numero=numero_clean).first()
        if existente:
            raise DuplicateEntityException(f"Ya existe un equipo registrado con el número de inventario '{numero_clean}'.")
        
        if id_salon:
            CampusService.get_salon_by_id(id_salon, active_only=True)

        equipo = Equipo(
            numero=numero_clean,
            descripcion=descripcion,
            id_salon=id_salon
        )
        db.session.add(equipo)
        db.session.commit()
        return equipo

    @staticmethod
    def get_equipment_by_id(id_equipo, active_only=True):
        query = Equipo.query.filter_by(id_equipo=id_equipo)
        if active_only:
            query = query.filter_by(activo=True)
        equipo = query.first()
        if not equipo:
            raise EntityNotFoundException(f"El equipo con ID {id_equipo} no existe o está inactivo.")
        return equipo

    @staticmethod
    def list_equipments(active_only=True, id_salon=None):
        query = Equipo.query
        if active_only:
            # Filtrar equipos activos en salones activos (si están asignados a un salón)
            # Equipos sin salón asignado (almacenamiento) pero activos también se listan
            query = query.filter(Equipo.activo == True)
        
        if id_salon:
            query = query.filter(Equipo.id_salon == id_salon)
            
        return query.all()

    @staticmethod
    def update_equipment(id_equipo, numero, descripcion, id_salon=None):
        equipo = EquipmentService.get_equipment_by_id(id_equipo, active_only=True)
        
        if not numero or not str(numero).strip():
            raise InvalidDataException("El número de inventario no puede estar vacío.")
            
        numero_clean = str(numero).strip()
        
        # Validar duplicidad si cambia el número
        if numero_clean != equipo.numero:
            existente = Equipo.query.filter_by(numero=numero_clean).first()
            if existente:
                raise DuplicateEntityException(f"Ya existe otro equipo registrado con el número de inventario '{numero_clean}'.")

        if id_salon:
            CampusService.get_salon_by_id(id_salon, active_only=True)

        equipo.numero = numero_clean
        equipo.descripcion = descripcion
        equipo.id_salon = id_salon
        db.session.commit()
        return equipo

    @staticmethod
    def delete_equipment(id_equipo):
        equipo = EquipmentService.get_equipment_by_id(id_equipo, active_only=True)
        equipo.activo = False
        db.session.commit()
        return {"message": f"Equipo {id_equipo} desactivado lógicamente."}

    @staticmethod
    def assign_software(id_equipo, id_programa):
        # Obtener equipo y validar que esté activo
        equipo = EquipmentService.get_equipment_by_id(id_equipo, active_only=True)
        
        # Obtener programa y validar que esté activo
        programa = ProgramService.get_program_by_id(id_programa, active_only=True)
        
        if programa in equipo.programas:
            # Ya está asignado
            return equipo
            
        equipo.programas.append(programa)
        db.session.commit()
        return equipo

    @staticmethod
    def remove_software(id_equipo, id_programa):
        """Elimina físicamente el registro de la relación de la tabla intermedia 'software'."""
        equipo = EquipmentService.get_equipment_by_id(id_equipo, active_only=True)
        programa = ProgramService.get_program_by_id(id_programa, active_only=True)
        
        if programa in equipo.programas:
            equipo.programas.remove(programa)
            db.session.commit()
            
        return {"message": f"Software {id_programa} desinstalado del equipo {id_equipo} exitosamente."}


class ProgramService:
    @staticmethod
    def create_program(nombre, descripcion=None):
        if not nombre or not nombre.strip():
            raise InvalidDataException("El nombre del programa es obligatorio y no puede estar vacío.")
            
        programa = Programa(nombre=nombre.strip(), descripcion=descripcion)
        db.session.add(programa)
        db.session.commit()
        return programa

    @staticmethod
    def get_program_by_id(id_programa, active_only=True):
        query = Programa.query.filter_by(id_programa=id_programa)
        if active_only:
            query = query.filter_by(activo=True)
        programa = query.first()
        if not programa:
            raise EntityNotFoundException(f"El programa con ID {id_programa} no existe o está inactivo.")
        return programa

    @staticmethod
    def list_programs(active_only=True):
        query = Programa.query
        if active_only:
            query = query.filter_by(activo=True)
        return query.all()

    @staticmethod
    def update_program(id_programa, nombre, descripcion=None):
        programa = ProgramService.get_program_by_id(id_programa, active_only=True)
        if not nombre or not nombre.strip():
            raise InvalidDataException("El nombre del programa no puede estar vacío.")
            
        programa.nombre = nombre.strip()
        programa.descripcion = descripcion
        db.session.commit()
        return programa

    @staticmethod
    def delete_program(id_programa):
        programa = ProgramService.get_program_by_id(id_programa, active_only=True)
        programa.activo = False
        db.session.commit()
        return {"message": f"Programa {id_programa} desactivado lógicamente."}
